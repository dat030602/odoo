from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    qty_ordered = fields.Float(string='ĐH đã duyệt SL', digits='Product Unit of Measure')
    qty_order_delivered = fields.Float(string='ĐH đã giao SL', digits='Product Unit of Measure')

    qty_can_order = fields.Float(string='Còn lại SL', digits='Product Unit of Measure', compute='_compute_qty_can_order')

    def _compute_qty_can_order(self):
        for rec in self:
            warehouse_id = self.env.context.get('warehouse')
            if warehouse_id:
                qty_available = rec.with_context(warehouse=warehouse_id).qty_available
            else:
                qty_available = rec.qty_available
            rec.qty_can_order = qty_available - (rec.qty_ordered - rec.qty_order_delivered)

    def _compute_qty_ordered(self):
        SaleSignLine = self.env['sale.sign.requests.line']

        for rec in self:
            rec.qty_ordered = 0

            domain = [
                ('sign_requests_id.state', 'in', ['approved', 'approve']),
                ('product_id', '=', rec.id),
                ('product_uom_qty', '!=', 0),
            ]

            lines = SaleSignLine.search(domain).filtered(lambda l: l.sign_requests_id.sale_order_id.delivery_status != 'full')
            rec.qty_order_delivered = sum(lines.mapped('sale_order_line_id.qty_delivered'))
            rec.qty_ordered = sum([l.product_uom._compute_quantity(l.product_uom_qty, rec.uom_id) for l in lines])
    
    def _cron_update_qty_ordered(self):
        SaleSignLine = self.env['sale.sign.requests.line']
        domain = [
            ('sign_requests_id.state', 'in', ['approved', 'approve']),
            ('product_uom_qty', '!=', 0),
        ]
        lines = SaleSignLine.search(domain).filtered(lambda l: l.sign_requests_id.sale_order_id.delivery_status != 'full')
        products = lines.mapped('product_id')
        for product in products:
            product._compute_qty_ordered()