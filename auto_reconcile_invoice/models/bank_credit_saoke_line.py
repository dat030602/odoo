# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class BankCreditSaokeLine(models.Model):
    _name = 'bank.credit.saoke.line'
    _description = 'Số dư có ngân hàng'
    _order = 'transaction_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='STT', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    accounting_date = fields.Char(string="Ngày hạch toán")
    transaction_description = fields.Text(string="Mô tả giao dịch")
    credit = fields.Monetary(string="Có", tracking=True)
    account_balance = fields.Monetary(string="Số dư TK", tracking=True)
    transaction_number = fields.Char(string="Số giao dịch", index=True)
    corresponsive_account = fields.Char(string="Số tài khoản đối ứng")
    corresponsive_name = fields.Char(string="Tên tài khoản đối ứng")
    mtid_citad = fields.Char(string="MTID/CITAD")
    to_virtual_account = fields.Char(string="Mã định danh TK thụ hưởng")
    transaction_date = fields.Char(string="Ngày phát sinh giao dịch", index=True)
    bank_code = fields.Char(string="Mã ngân hàng")
    
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bank.credit.saoke.line') or _('New')
                
        return super().create(vals_list)
