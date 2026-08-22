from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    advance_payment_method = fields.Selection(
        selection_add=[('select_lines', 'Select lines')],
        ondelete={'select_lines': 'set default'}
    )
    
    custom_line_ids = fields.One2many('sale.advance.payment.inv.line', 'wizard_id', string="Custom Line Details")

    @api.onchange('advance_payment_method')
    def _onchange_advance_payment_method(self):
        if self.advance_payment_method == 'select_lines':
            sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
            lines = []
            self.custom_line_ids = [(5, 0, 0)]  # Clear existing lines
            for so in sale_orders:
                for line in so.order_line.filtered(lambda l: l.display_type == False and l.qty_to_invoice > 0):
                    lines.append((0, 0, {
                        'sale_line_id': line._origin.id,
                        'qty_to_invoice': line.qty_to_invoice,
                    }))
            self.custom_line_ids = lines
            self.custom_line_ids._onchange_price_total()

    def create_invoices(self):
        if self.advance_payment_method == 'select_lines':
            custom_line_ids = self.custom_line_ids.filtered(lambda l: l.is_select and l.qty_to_invoice > 0)
            if not custom_line_ids:
                raise ValidationError(_("Please select at least 1 line to create invoice."))

            moves = self.env['account.move']
            sale_orders = self.sale_order_ids[0] if self.sale_order_ids else self.env['sale.order']
            move_vals = self.sale_order_ids._prepare_invoice()
            move_vals['invoice_line_ids'] = []
            
            for custom_line in custom_line_ids:
                line_vals = custom_line.sale_line_id._prepare_invoice_line(
                    sequence=custom_line.sale_line_id.sequence
                )
                line_vals['quantity'] = custom_line.qty_to_invoice
                move_vals['invoice_line_ids'].append((0, 0, line_vals))
            
            moves |= self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create([move_vals])
            
            if moves:
                return self.sale_order_ids.action_view_invoice(invoices=moves)
            return {'type': 'ir.actions.act_window_close'}
            
        return super().create_invoices()

