from odoo import models, fields, api
from datetime import date, datetime

class SaleOrderLineToInvoiceWizard(models.TransientModel):
    _name = 'sale.order.to.invoice'
    _description = 'Wizard chọn dòng đơn hàng để tạo hóa đơn'

    sale_order_id = fields.Many2one('sale.order', string="Đơn hàng", required=True)
    line_ids = fields.One2many('sale.order.to.invoice.line', 'wizard_id', string="Dòng đơn hàng")

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Tự động lấy các dòng đơn hàng khi chọn đơn hàng."""
        if self.sale_order_id:
            self.line_ids = [(5, 0, 0)]
            lines = []
            for line in self.sale_order_id.order_line:
                lines.append((0, 0, {
                    'order_line_id': line.id,
                    'product_id': line.product_id.id,
                    'uom_qty': line.product_uom_qty,
                }))
            self.line_ids = lines

    def action_create_invoice(self):
        invoice_vals = {
            'date': datetime.now().date(),
            'invoice_date': datetime.now().date(),
            'move_type': 'out_invoice',
            'partner_id': self.sale_order_id.partner_id.id,
            'invoice_origin': self.sale_order_id.origin,
            'invoice_line_ids': [],
            'invoice_payment_term_id': self.sale_order_id.payment_term_id.id if self.sale_order_id else False,
        }
        for line in self.line_ids:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.uom_qty,
                'price_unit': line.order_line_id.price_unit,
                'name': line.order_line_id.name,
            }))
        invoice = self.env['account.move'].create(invoice_vals)

        # Ánh xạ dòng hóa đơn với dòng đơn hàng
        if self.sale_order_id:
            invoice_lines = invoice.invoice_line_ids
            product_ids = invoice_lines.mapped('product_id').mapped('id')
            sale_order_lines = self.sale_order_id.order_line.filtered(lambda l:l.product_id.id in product_ids)
            for sale_line, invoice_line in zip(sale_order_lines, invoice_lines):
                invoice_line.write({'sale_line_ids': [(4, sale_line.id)]})

