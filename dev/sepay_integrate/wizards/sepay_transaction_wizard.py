# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SePayTransactionWizard(models.TransientModel):
    _name = 'sepay.transaction.wizard'
    _description = 'SePay Transaction Detail Wizard'

    transaction_id = fields.Char(string='Transaction ID', readonly=True)
    account_number = fields.Char(string='Account Number', readonly=True)
    transaction_content = fields.Text(string='Transaction Content', readonly=True)
    amount_in = fields.Float(string='Amount In', readonly=True)
    amount_out = fields.Float(string='Amount Out', readonly=True)
    accumulated = fields.Float(string='Accumulated Balance', readonly=True)
    transaction_date = fields.Datetime(string='Transaction Date', readonly=True)
    bank_brand_name = fields.Char(string='Bank Brand Name', readonly=True)
    reference_number = fields.Char(string='Reference Number', readonly=True)
    code = fields.Char(string='Code', readonly=True)
    sub_account = fields.Char(string='Sub Account', readonly=True)
    bank_account_id = fields.Char(string='Bank Account ID', readonly=True)

