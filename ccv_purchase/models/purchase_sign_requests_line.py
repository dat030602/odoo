# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

class PurchaseSignRequestsLine(models.Model):
    _name = 'purchase.sign.requests.line'
    _inherit = ['sign.requests.line']
    _description = 'Purchase Sign Requests Line'

    # Override sign_requests_id để sử dụng purchase.sign.requests
    sign_requests_id = fields.Many2one('purchase.sign.requests', string='Purchase Sign Requests', required=True, ondelete='cascade')
    
    # Field specific cho purchase
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Chi tiết đơn mua hàng', required=True, ondelete='cascade')

    def _convert_to_tax_base_line_dict(self):
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.purchase_order_line_id.order_id.partner_id,
            currency=self.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.product_uom_qty,
            price_subtotal=self.amount_untax,
        )
