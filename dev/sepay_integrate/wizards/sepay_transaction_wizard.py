# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SePayTransactionWizard(models.TransientModel):
    _name = 'sepay.transaction.wizard'
    _description = 'SePay Transaction Detail Wizard'

    sepay_id = fields.Integer(string='SePay ID', readonly=True, tracking=True)
    sepay_gateway = fields.Char(string='SePay Gateway', readonly=True, tracking=True)
    sepay_transaction_date = fields.Datetime(string='SePay Transaction Date', readonly=True, tracking=True)
    sepay_account_number = fields.Char(string='SePay Account Number', readonly=True, tracking=True)
    sepay_code = fields.Char(string='SePay Code', readonly=True, tracking=True)
    sepay_content = fields.Text(string='SePay Content', readonly=True, tracking=True)
    sepay_transfer_type = fields.Selection([
        ('in', 'In'),
        ('out', 'Out')
    ], string='SePay Transfer Type', readonly=True, tracking=True)
    sepay_transfer_amount = fields.Float(string='SePay Transfer Amount', readonly=True, tracking=True)
    sepay_sub_account = fields.Char(string='SePay Sub Account', readonly=True, tracking=True)
    sepay_reference_code = fields.Char(string='SePay Reference Code', readonly=True, tracking=True)
    sepay_description = fields.Text(string='SePay Description', readonly=True, tracking=True)

