# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class SignRequestsLine(models.Model):
    _name = 'sign.requests.line'
    _description = 'Sign Requests Line'

    sign_requests_id = fields.Many2one('sign.requests', string='Sign Requests', required=True, ondelete='cascade')
    
    name = fields.Text(string='Tên sản phẩm', readonly=True)
    packaging_image = fields.Binary(string='Hình ảnh sản phẩm', readonly=True, max_width=128, max_height=128)
    product_image = fields.Binary(string='Hình ảnh bao bì', readonly=True, max_width=128, max_height=128)
    product_id = fields.Many2one('product.product', string='Sản phẩm', readonly=True)
    product_uom_qty = fields.Float(string='Số lượng', readonly=True, digits="Product Unit of Measure")
    product_uom = fields.Many2one('uom.uom', string='Đơn vị', readonly=True)
    price_unit = fields.Monetary(string='Đơn giá', readonly=True, currency_field="currency_id")
    
    tax_id = fields.Many2many('account.tax', string='Thuế', readonly=True)
    amount_untax = fields.Monetary(string='Chưa thuế', readonly=True, currency_field="currency_id")
    amount_tax = fields.Monetary(string='Thuế', readonly=True, currency_field="currency_id")
    amount_total = fields.Monetary(string='Tổng cộng', readonly=True, currency_field="currency_id")
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', readonly=True)

    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.sign_requests_id.partner_id,
            currency=self.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.product_uom_qty,
            price_subtotal=self.amount_untax,
        )
