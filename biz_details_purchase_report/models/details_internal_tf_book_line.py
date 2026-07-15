# -*- coding: utf-8 -*-
from odoo import fields, models


class DetailsInternalTfBookLine(models.Model):
    _name = 'details.internal.tf.book.line'
    _description = 'Chi tiết sổ nhập hàng tại cảng'
    _order = 'date, id'

    parent_id = fields.Many2one('details.internal.tf.book', string='Sổ nhập hàng tại cảng', ondelete='cascade')

    date = fields.Date('Ngày chứng từ')
    name = fields.Char('Số chứng từ')
    partner_name = fields.Char('Tên nhà cung cấp')
    product_code = fields.Char('Mã hàng')
    product_name = fields.Char('Tên hàng')
    uom_name = fields.Char('ĐVT')
    warehouse_code = fields.Char('Mã kho')
    account = fields.Char('TK Kho')
    account_ctp = fields.Char('TK Đối ứng')
    exchange_rate = fields.Float('Tỷ giá', digits=(16, 3))
    price_unit = fields.Float('Đơn giá', digits='Product Price')
    price_unit_w_currency = fields.Float('Đơn giá NT', digits='Product Price')
    amount_total = fields.Float('Giá trị mua', digits='Product Price')
    amount_total_w_currency = fields.Float('Giá trị mua NT', digits='Product Price')
    quantity = fields.Float('Số lượng nhập', digits='Product Unit of Measure')
    return_quantity = fields.Float('Số lượng trả lại', digits='Product Unit of Measure')
    amount_total_return = fields.Float('Giá trị trả lại', digits='Product Price')
    amount_total_return_w_currency = fields.Float('Giá trị trả lại NT', digits='Product Price')
    order_name = fields.Char('Đơn mua hàng')
