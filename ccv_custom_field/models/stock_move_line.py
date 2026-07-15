from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    cur_location_stock_quant = fields.Float(string="Tồn kho Từ", related="move_id.cur_location_stock_quant")
    cur_location_dest_stock_quant = fields.Float(string="Tồn kho Đến", related="move_id.cur_location_dest_stock_quant")

