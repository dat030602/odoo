# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class SaleSignRequestsLine(models.Model):
    _name = 'sale.sign.requests.line'
    _inherit = ['sign.requests.line']
    _description = 'Sale Sign Requests Line'

    # Override sign_requests_id để sử dụng sale.sign.requests
    sign_requests_id = fields.Many2one('sale.sign.requests', string='Sale Sign Requests', required=True, ondelete='cascade')
    
    # Field specific cho sale
    sale_order_line_id = fields.Many2one('sale.order.line', string='Chi tiết đơn hàng')

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
