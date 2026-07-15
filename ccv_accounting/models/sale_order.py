from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_is_zero
from odoo import SUPERUSER_ID
from datetime import datetime, timedelta
import logging
import pytz
_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_to_export = fields.Float(string="Số lượng cần xuất", digits=(16, 3), copy=False, default=lambda self: self.product_uom_qty)

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        self.ensure_one()
        need_create_picking = self.env.context.get('need_create_picking', True)
        if not need_create_picking:
            return self.product_uom_qty
        res = super(SaleOrderLine, self)._get_qty_procurement(previous_product_uom_qty=previous_product_uom_qty)
        if self.qty_to_export:
            qty = 0.0
            outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves()
            for move in outgoing_moves.filtered(lambda l:l.state not in ('done','cancel')):
                qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
            for move in incoming_moves.filtered(lambda l:l.state not in ('done','cancel')):
                qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
            if self.qty_to_export > qty:
                qty_to_export = self.product_uom_qty - (self.qty_to_export - qty)
                res = qty_to_export
            else:
                res = self.product_uom_qty
        return res

    # @api.onchange("product_uom_qty")
    # def _onchange_product_uom_qty_qty_to_export(self):
    #     for rec in self:
    #         rec.qty_to_export = rec.product_uom_qty

    # @api.constrains('qty_to_export', 'product_uom_qty')
    # def _check_qty_to_export(self):
    #     for line in self:
    #         if line.qty_to_export > line.product_uom_qty:
    #             raise UserError(_('Số lượng cần xuất không được lớn hơn số lượng đã đặt hàng.'))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        for rec in self:
            partner = rec.partner_id.commercial_partner_id
            if partner.is_prevent_over_credit and (rec.partner_credit_warning != '' and rec.partner_credit_warning != False):
                raise UserError("Vui lòng kiểm tra tín dụng của khách hàng!!!")
        self = self.with_context(need_create_picking=False)
        res = super(SaleOrder, self).action_confirm()
        return res

    def _get_vals_create_pk(self, time=0):
        context = self.env.context
        date = context.get("date", False)
        if not date:
            date = fields.Datetime.now()
        vals = {
            'need_create_invoice': True,
            'stock_date_receipt': date + timedelta(days=time),
            'scheduled_date': date + timedelta(days=time),
            'reason_output_input_stock': 'Xuất kho bán hàng',
        }
        return vals

    def action_create_picking_f_input_1(self):
        for order in self.sudo():
            for line in order.order_line:
                qty = line.qty_delivered - line.product_uom_qty
                if qty < 0:
                    line.qty_to_export = abs(qty)
        self._action_create_picking_f_input_1()

    def _action_create_picking_f_input_1(self):
        for order in self.sudo():
            pickings = order.picking_ids.filtered(lambda p: p.state not in ['cancel'])
            if not pickings:
                continue
            
            for picking in pickings:
                group_id = picking.group_id
                picking.need_create_invoice = True
                remaining_moves = []
                for line in order.order_line.filtered(lambda l:l.display_type == '' or l.display_type is False):
                    if line.qty_to_export > 0:
                        remaining_moves.append((0, 0, {
                            'name': order.name,
                            'partner_id': picking.partner_id.id,
                            'product_id': line.product_id.id,
                            'product_uom_qty': line.qty_to_export,
                            'product_uom': line.product_uom.id,
                            'location_id': picking.location_id.id,
                            'location_dest_id': picking.location_dest_id.id,
                            'sale_line_id': line.id,
                            'group_id': picking.group_id.id,
                        }))

                if remaining_moves:
                    vals = self._get_vals_create_pk()
                    vals.update({'move_ids': remaining_moves})
                    if group_id:
                        new_group_id = group_id.copy({'sale_id':order.id})
                        vals.update({'group_id':new_group_id.id})
                    new_picking = picking.copy(vals)
                    order.picking_ids |= new_picking

                for line in order.order_line:
                    line.qty_to_export = 0
                break

    def action_create_picking_f_input(self):
        for order in self.sudo():
            utc_now = fields.Datetime.now()
            user_tz = self.env.user.tz or 'UTC'
            timezone = pytz.timezone(user_tz)
            localized_time = pytz.utc.localize(utc_now).astimezone(timezone).replace(tzinfo=None)
            
            pickings = order.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel'])
            if not pickings:
                continue
            
            for picking in pickings:
                picking.move_ids.with_user(SUPERUSER_ID).write({'state':'draft'})
                picking.stock_date_receipt = localized_time

                move_lines = picking.move_ids_without_package
                group_id = picking.group_id
                picking.need_create_invoice = True
                remaining_moves = []
                for move in move_lines:
                    sale_line = move.sale_line_id
                    if sale_line.qty_to_export > 0:
                        move.write({'product_uom_qty': sale_line.qty_to_export})
                        remaining_qty = sale_line.product_uom_qty - sale_line.qty_to_export
                        if remaining_qty > 0:
                            remaining_moves.append((0, 0, {
                                'name': sale_line.name,
                                'partner_id': picking.partner_id.id,
                                'product_id': move.product_id.id,
                                'product_uom_qty': remaining_qty,
                                'product_uom': move.product_uom.id,
                                'location_id': picking.location_id.id,
                                'location_dest_id': picking.location_dest_id.id,
                                'sale_line_id': sale_line.id,
                                'group_id': move.group_id.id,
                            }))
                    else:
                        remaining_moves.append((0, 0, {
                            'name': sale_line.name,
                            'partner_id': picking.partner_id.id,
                            'product_id': move.product_id.id,
                            'product_uom_qty': move.product_uom_qty,
                            'product_uom': move.product_uom.id,
                            'location_id': picking.location_id.id,
                            'location_dest_id': picking.location_dest_id.id,
                            'sale_line_id': sale_line.id,
                            'group_id': move.group_id.id,
                        }))
                        move.unlink()

                if remaining_moves:
                    vals = self._get_vals_create_pk(time=1)
                    vals.update({'move_ids': remaining_moves})
                    if group_id:
                        new_group_id = group_id.copy({'sale_id':order.id})
                        vals.update({'group_id':new_group_id.id})
                    new_picking = picking.copy(vals)
                    order.picking_ids |= new_picking

            for line in order.order_line:
                line.qty_to_export = 0

    def action_view_invoice_auto(self, invoices):
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
                'default_partner_id': self.partner_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.name,
            })
        action['context'] = context
        return action

    def action_create_invoice_f_so(self):
        self.ensure_one()

        invoice_vals = self._prepare_invoice()
        invoice_vals.update({
            'date': datetime.now().date(),
            'invoice_date': datetime.now().date(),
        })
        invoice_line_vals = []
        order_line = self.order_line.filtered(lambda l:l.display_type == '' or l.display_type is False)
        qty_delivered = sum(order_line.mapped('qty_delivered'))
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        for line in order_line:
            qty = line.qty_delivered if qty_delivered > 0 else line.product_uom_qty
            qty -= line.qty_invoiced
            if qty > 0:
                line_data = line._prepare_invoice_line(sequence=invoice_item_sequence)
                line_data.update({'quantity': qty})
                invoice_line_vals.append(Command.create(line_data))
                invoice_item_sequence += 1
        invoice_vals['invoice_line_ids'] += invoice_line_vals
        if len(invoice_vals['invoice_line_ids']) == 0:
            raise UserError("Không còn dòng hóa đơn để xuất !!!")
        invoice = self.env['account.move'].sudo().create(invoice_vals)

        # Ánh xạ dòng hóa đơn với dòng đơn hàng
        # self.match_order_inv(invoice)
        invoice.action_post()
        invoice.message_post_with_view(
            'mail.message_origin_link',
            values={'self': invoice, 'origin': self},
            subtype_id=self.env.ref('mail.mt_note').id)
        
        return self.action_view_invoice_auto(invoice)

    def action_launch_stock_rule(self, order_line=False):
        if not order_line:
            order_line = self.order_line
        for line in order_line.filtered(lambda l:l.display_type is False and l.product_uom_qty > 0):
            line._action_launch_stock_rule()
        for order in self.sudo():
            pickings_to_confirm = order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
            pickings_to_confirm.action_reset_to_draft()
            picking_vals = order._get_vals_create_pk()
            pickings_to_confirm.write(picking_vals)
        order_line.qty_to_export = 0

    def match_order_inv(self, invoice):
        for order in self:
            product_to_sale_line = {
                l.product_id.id: l
                for l in order.order_line
                if l.product_uom_qty > 0
            }
            for invoice_line in invoice.invoice_line_ids:
                product_id = invoice_line.product_id.id
                sale_line = product_to_sale_line.get(product_id)
                if sale_line:
                    invoice_line.write({'sale_line_ids': [(4, sale_line.id)]})
