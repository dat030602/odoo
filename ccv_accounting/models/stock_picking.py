from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tests import Form
from datetime import date, datetime
from odoo.fields import Command
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    need_create_invoice = fields.Boolean(string="Cần xuất hóa đơn", default=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 
        string='Mã công trình / Analytic Account'
    )
    is_sale = fields.Boolean(compute="_compute_is_sale_picking")
    is_purchase = fields.Boolean(compute="_compute_is_purchase_picking")
    partner_credit_warning = fields.Text(compute='_compute_partner_credit_warning')

    @api.depends('company_id', 'partner_id', 'sale_id')
    def _compute_partner_credit_warning(self):
        for rec in self:
            rec.partner_credit_warning = ''
            if not rec.sale_id:
                continue
            order = rec.sale_id
            show_warning = rec.state not in ('cancel', 'done') and rec.company_id.account_use_credit_limit
            if show_warning:
                total_amount = sum([line.sale_line_id.price_unit * line.sale_line_id.product_uom._compute_quantity(line.quantity_done, line.sale_line_id.product_uom) for line in rec.move_ids.filtered(lambda l: l.product_id.type == 'product' and l.sale_line_id)])
                updated_credit = rec.partner_id.commercial_partner_id.credit + (total_amount / order.currency_rate)
                rec.partner_credit_warning = self.env['account.move'].sudo()._build_credit_warning_message(rec, updated_credit)

    @api.depends("sale_id")
    def _compute_is_sale_picking(self):
        for rec in self:
            if rec.sale_id:
                rec.is_sale = True
            else:
                rec.is_sale = False

    @api.depends("purchase_id")
    def _compute_is_purchase_picking(self):
        for rec in self:
            if rec.purchase_id:
                rec.is_purchase = True
            else:
                rec.is_purchase = False

    def action_create_invoice(self):
        for picking in self.sudo():
            if picking.need_create_invoice and picking.sale_id:
                invoice_vals = picking.sale_id._prepare_invoice()
                invoice_vals.update({
                    'date': picking.stock_date_receipt.date(),
                    'invoice_date': picking.stock_date_receipt.date(),
                })
                invoice_line_vals = []
                order_line = picking.move_ids.mapped('sale_line_id').filtered(lambda l:l.product_uom_qty > l.qty_invoiced)
                invoice_item_sequence = 0
                for line in order_line:
                    move = picking.move_ids.filtered(lambda l:l.sale_line_id == line)
                    qty = sum(move.mapped('quantity_done'))
                    if qty > 0:
                        line_data = line._prepare_invoice_line(sequence=invoice_item_sequence)
                        line_data.update({'quantity': qty})
                        invoice_line_vals.append(Command.create(line_data))
                        invoice_item_sequence += 1
                invoice_vals['invoice_line_ids'] += invoice_line_vals
                invoice = self.env['account.move'].sudo().create(invoice_vals)

                # Ánh xạ dòng hóa đơn với dòng đơn hàng
                # if picking.sale_id:
                    # picking.sale_id.match_order_inv(invoice)
                invoice.action_post()
            if picking.need_create_invoice:
                picking.need_create_invoice = False
        return

    def auto_create_invoice(self):
        for picking in self:
            purchase_id = picking.purchase_id
            purchase_line_ids = purchase_id.order_line
            if picking.need_create_invoice and picking.purchase_id:
                purchase_line_in_move = picking.move_ids.mapped('purchase_line_id')
                for move_id in picking.move_ids:
                    move_id.purchase_line_id.qty_to_invoice = move_id.quantity_done
                (purchase_line_ids - purchase_line_in_move).write({'qty_to_invoice': 0})
                
                wizard_action = picking.purchase_id.action_create_invoice_ccv()
                if wizard_action and wizard_action.get('res_model') == 'wz.purchase.invoive':
                    wizard = Form(self.env[wizard_action['res_model']].with_context(wizard_action['context'])).save()
                    if wizard and picking.state == 'done':
                        wizard.action_confirm()

            if picking.need_create_invoice and picking.state == 'done':
                picking.need_create_invoice = False
            for am in picking.move_ids.purchase_line_id.invoice_lines.move_id.filtered(lambda l:l.state == 'draft'):
                am.action_post()
            purchase_line_ids._compute_qty_invoiced()

        return 

    def button_validate(self):
        res = super(StockPicking, self.with_context(skip_immediate=True, manual_validate_date_time=self.stock_date_receipt)).button_validate()
        partner = self.partner_id.commercial_partner_id
        if partner.is_prevent_over_credit and (self.partner_credit_warning != '' and self.partner_credit_warning != False):
            raise UserError("Khách hàng bị chặn hoạt động khi vượt tín dụng!!!")
        if self.is_sale:
            self.action_create_invoice()
        elif self.is_purchase:
            self.auto_create_invoice()
        return res

    def action_reset_to_draft(self):
        for picking in self:
            if picking.state != 'done':
                self.do_unreserve()
                self.move_ids.write({'state':'draft'})

    def action_get_account_moves(self):
        self.ensure_one()
        action_data = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action_data['domain'] = [('id', 'in', self.move_ids.mapped('account_move_ids').ids)]
        return action_data

    def action_view_invoice(self):
        self.ensure_one()
        invoices = self.move_ids.mapped('sale_line_id').mapped('invoice_lines').mapped('move_id')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.sale_id.partner_id.id,
                'default_partner_shipping_id': self.sale_id.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.sale_id.payment_term_id.id or self.sale_id.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.sale_id.name,
            })
        action['context'] = context
        return action

    

