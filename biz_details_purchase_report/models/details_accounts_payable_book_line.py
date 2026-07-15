# -*- coding: utf-8 -*-
from odoo import models, fields


class DetailsAccountsPayableBookLine(models.Model):
    _name = 'details.accounts.payable.book.line'
    _description = 'Chi tiết dòng công nợ phải trả'

    parent_id = fields.Many2one('details.accounts.payable.book', ondelete='cascade')

    partner_id = fields.Many2one('res.partner', string='Khách hàng')
    partner_code = fields.Char(string='Mã KH')
    partner_type = fields.Char(string='Loại')
    invoice_date = fields.Date(string='Ngày hạch toán')
    date = fields.Date(string='Ngày chứng từ')
    move_id = fields.Many2one('account.move', string='Số chứng từ')
    reference = fields.Char(string='Số hoá đơn')
    note = fields.Char(string='Diễn giải')
    account_id = fields.Many2one('account.account', string='TK công nợ')
    account_dest_id = fields.Many2one('account.account', string='TK đối ứng')
    amount_tax = fields.Float(string='Thuế')
    debit = fields.Float(string='PS nợ')
    credit = fields.Float(string='PS có')
    end_debit = fields.Float(string='SD nợ')
    end_credit = fields.Float(string='SD có')
    product_uom_qty = fields.Float(string='Số lượng')
    price_unit = fields.Float(string='Đơn giá')
    uom_id = fields.Many2one('uom.uom', string='ĐVT')
