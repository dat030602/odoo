import ast
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    qty_to_check = fields.Float(string='Số lượng cần kiểm tra', digits='Product Unit of Measure', compute='_compute_qty_to_check', store=True)

    @api.depends('product_min_qty', 'qty_on_hand')
    def _compute_qty_to_check(self):
        for rec in self:
            rec.qty_to_check = rec.product_min_qty - rec.qty_on_hand
