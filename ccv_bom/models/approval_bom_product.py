from odoo import models, fields,api
import logging
import ast
import datetime
import calendar
import pytz

_logger = logging.getLogger(__name__)

class ApprovalBomProduct(models.Model):
    _name = 'approval.bom.product'

    name = fields.Char(string="Tên sản phẩm", related="product_id.name")

    # Định mức chỉ may
    product_id = fields.Many2one(string="Sản phẩm", comodel_name="product.product")
    service_id = fields.Many2one(string="Dịch vụ", comodel_name="product.product", domain="[('detailed_type', '=', 'service')]")

    qty_norm_25kg = fields.Float(string="Định mức bao 25kg", digits="Product Unit of Measure")
    qty_norm_50kg = fields.Float(string="Định mức bao 50kg", digits="Product Unit of Measure")
    uom_25kg_id = fields.Many2one(string="Đơn vị tính 25kg", comodel_name="uom.uom")
    uom_50kg_id = fields.Many2one(string="Đơn vị tính 50kg", comodel_name="uom.uom")
    
    # Định mức xăng dầu
    partner_id = fields.Many2one(string="Đối tác", comodel_name="res.partner")
    qty_norm_fuel = fields.Float(string="Định mức xăng dầu", digits="Product Unit of Measure")

    price_unit = fields.Monetary(string="Đơn giá", currency_field="currency_id")
    currency_id = fields.Many2one(string="Tiền tệ", comodel_name="res.currency", default=lambda self: self.env.company.currency_id)

