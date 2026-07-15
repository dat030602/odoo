from odoo import models, fields, api

class SaleOrderLineToInvoiceLine(models.TransientModel):
    _name = 'sale.order.to.invoice.line'
    _description = 'Dòng đơn hàng trong wizard'

    wizard_id = fields.Many2one('sale.order.to.invoice', string="Wizard")
    order_line_id = fields.Many2one('sale.order.line', string="Dòng đơn hàng", required=True)
    product_id = fields.Many2one('product.product', string="Sản phẩm", related='order_line_id.product_id', readonly=True)
    uom_qty = fields.Float(string="Số lượng", required=True)

    @api.onchange('order_line_id')
    def _onchange_order_line_id(self):
        """Tự động điền số lượng từ sale.order.line khi chọn dòng đơn hàng"""
        if self.order_line_id:
            self.uom_qty = self.order_line_id.product_uom_qty
