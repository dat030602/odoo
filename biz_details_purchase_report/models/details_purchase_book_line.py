# -*- coding: utf-8 -*-
from odoo import fields, models


class DetailsPurchaseBookLine(models.Model):
    _name = 'details.purchase.book.line'
    _description = 'Chi tiết sổ chi tiết mua hàng'
    _order = 'date, id'

    parent_id = fields.Many2one('details.purchase.book', string='Sổ chi tiết mua hàng')

    date = fields.Date('Ngày chứng từ')
    name = fields.Char('Số chứng từ')
    partner_name = fields.Char('Tên nhà cung cấp')
    product_code = fields.Char('Mã hàng')
    product_name = fields.Char('Tên hàng')
    product_uom_id = fields.Char('ĐVT')
    quantity = fields.Float('Số lượng mua', digits='Product Unit of Measure')
    exchange_rate = fields.Float('Tỷ giá', digits=(16, 3))
    unit_price_nt = fields.Float('Đơn giá NT', digits='Product Price')
    unit_price = fields.Float('Đơn giá', digits='Product Price')
    purchase_value_nt = fields.Float('Giá trị mua NT', digits='Product Price')
    purchase_value = fields.Float('Giá trị mua', digits='Product Price')
    location_dest_id = fields.Char('Mã kho')
    account_debit = fields.Char('TK Nợ')
    account_credit = fields.Char('TK Có')
    order_name = fields.Char('Đơn mua hàng')
