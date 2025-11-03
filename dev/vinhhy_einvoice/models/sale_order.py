# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    vh_einv_ids = fields.Many2many('vinhhy.einvoice', 'vh_einv_sale_order_rel', 'sale_id','vh_einv_id', string='Vinh Hy E-Invoice', copy=False)
    vh_einv_ref = fields.Char('VH E-Invoice Reference', compute='_compute_vh_einv_ref', store=True, tracking=True)
    vh_einv_count = fields.Integer('VH E-Invoices Count', compute='_compute_vh_einv_ref')

    @api.depends('vh_einv_ids', 'vh_einv_ids.state', 'vh_einv_ids.name')
    def _compute_vh_einv_ref(self):
        for move in self:
            issued_ei = move.vh_einv_ids.filtered(lambda einv: einv.state == 'CM')
            move.vh_einv_ref = ' - '.join(sorted(issued_ei.mapped('name')))
            move.vh_einv_count = len(issued_ei.ids)

    def action_create_einvoice(self):
        if not self.partner_invoice_id:
            raise UserError(_("You must have partner to invoice!"))
        vinhhy_einv_val = {
            'sale_ids': [(4, self.id)],
            'partner_id': self.partner_invoice_id and self.partner_invoice_id.id or False,
            'date_invoice': self.date_order,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'fiscal_position_id': self.partner_invoice_id.property_account_position_id.id,
            'user_id': self.user_id.id if self.user_id else False,
            'team_id': self.team_id.id if self.team_id else False,
            'customer_email': self.partner_invoice_id and self.partner_invoice_id.email or False,
        }
        einv_line_vals = self._prepare_einv_line_values()
        vinhhy_einv_val['line_ids'] = einv_line_vals
        self.env['vinhhy.einvoice'].create(vinhhy_einv_val)
        return self.action_view_vh_einv(create=True)

    def _prepare_einv_line_values(self):
        line_vals = []
        for line in self.order_line.filtered(lambda l: l.display_type is False):
            name = line.product_id.name or ''
            # Recompute tax for VAT Invoice
            val = (0, 0, {
                'name': name,
                'price_unit': line.price_unit,
                'quantity': line.product_uom_qty,
                'discount': line.discount,
                'uom_id': line.product_id.uom_id.id,
                'product_id': line.product_id.id or False,
                'tax_id': line.tax_id[0] if line.tax_id else False,
                'sale_line_id': line.id #FIXME
            })
            line_vals.append(val)
        return line_vals

    def action_view_vh_einv(self, create=False):
        self.ensure_one()
        invs = self.vh_einv_ids
        if len(invs) == 1:
            return {
                'name': _('E-Invoice'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'vinhhy.einvoice',
                'target': 'current',
                'res_id': invs.id,
                'context': dict(self.env.context, create=False)
            }
        else:
            domain = [('id', 'in', invs.ids)]
            if create:
                domain = domain + [('einv_type', '=', 'origin')]
            return {
                'name': _('Vinh Hy E-Invoice'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'vinhhy.einvoice',
                'target': 'current',
                'domain': domain,
                'context': dict(self.env.context, create=False)
            }  
