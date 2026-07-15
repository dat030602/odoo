from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ccv_sale_plan_export_line_mixin(models.Model):
    _name = 'ccv.sale.plan.export.line.mixin'
    _order = "team_id,partner_id,date,order_id"

    date = fields.Date(string='Ngày đặt hàng')
    order_id = fields.Many2one('sale.order',string="Đơn hàng")
    line_id = fields.Many2one('sale.order.line', string="Dòng đơn hàng", ondelete="cascade")
    partner_id = fields.Many2one('res.partner',string="Khách hàng")
    product_id = fields.Many2one('product.product',string="Sản phẩm")
    name = fields.Char(string='Tên')
    product_uom_id = fields.Many2one('uom.uom',string="Đơn vị tính")
    product_uom_qty = fields.Float(string='SL đặt', digits="Product Unit of Measure")
    qty_delivery = fields.Float(string='SL giao', digits="Product Unit of Measure")
    qty_delivered = fields.Float(string='SL đã giao', digits="Product Unit of Measure")
    qty_available = fields.Float(string='Tồn kho', digits="Product Unit of Measure")
    qty_mrp = fields.Float(string='SL sản xuất', digits="Product Unit of Measure")
    note = fields.Char(string='Ghi chú')
    description = fields.Text(string='Diễn giải')
    team_id = fields.Many2one('crm.team',string="Khu vực")
    is_promotional_product = fields.Boolean()

    @api.onchange("qty_delivery", "qty_available")
    def _onchange_qty_delivery(self):
        for rec in self:
            rec.qty_mrp = rec.qty_delivery - rec.qty_available if rec.qty_delivery > rec.qty_available else 0

    @api.onchange("line_id")
    def _onchange_line_id(self):
        for rec in self:
            if rec.line_id:
                if rec.product_uom_qty != rec.line_id.product_uom_qty:
                    rec.product_uom_qty = rec.line_id.product_uom_qty
                if rec.qty_delivered != rec.line_id.qty_delivered:
                    rec.qty_delivered = rec.line_id.qty_delivered
                    
    def get_clean_name(self):
        self.ensure_one()
        if self.name and ']' in self.name:
            return self.name.split(']', 1)[1].strip()
        return self.name
