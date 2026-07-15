# -*- coding: utf-8 -*-
from odoo import models, fields


class SummaryAccountsPayableBookLine(models.Model):
    _name = 'summary.accounts.payable.book.line'
    _description = 'Dòng Tổng hợp công nợ phải trả'

    parent_id = fields.Many2one('summary.accounts.payable.book', ondelete='cascade')

    partner_id = fields.Many2one('res.partner', string='Nhà cung cấp')
    customer_name = fields.Char(string='Tên nhà cung cấp')
    customer_code = fields.Char(string='Mã nhà cung cấp')
    vat = fields.Char(string='Mã số thuế')
    address = fields.Char(string='Địa chỉ')
    start_debit = fields.Float(string='Nợ đầu kỳ')
    start_credit = fields.Float(string='Có đầu kỳ')
    ps_debit = fields.Float(string='PS nợ')
    ps_credit = fields.Float(string='PS có')
    end_debit = fields.Float(string='Nợ cuối kỳ')
    end_credit = fields.Float(string='Có cuối kỳ')
