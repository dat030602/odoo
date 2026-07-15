from odoo import models, fields,api
import logging

_logger = logging.getLogger(__name__)

class StockReportparticipant(models.Model):
    _name = "stock.ccv.report.stock.quant"

    name = fields.Char(string="Tên", related="product_id.name")
    default_code = fields.Char(string="Mã sản phẩm", related="product_id.default_code")
    location_id = fields.Many2one('stock.location',string="Vị trí")
    product_id = fields.Many2one('product.product',string="Sản phẩm")
    uom_id = fields.Many2one('uom.uom',string="ĐVT", related="product_id.uom_id")
    quantity = fields.Float(string="Số lượng")
    inventory_quantity = fields.Float(string="Số lượng đã đếm", digits=(16,3))
    diff_quantity = fields.Float(string="Chênh lệch", digits=(16,3))
    report_line_id = fields.Many2one('stock.ccv.report.line2', digits=(16,3))
    location_dest_id = fields.Many2one("stock.location", "Kho kiểm kê")
