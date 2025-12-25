# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class CassoTransactionWizard(models.TransientModel):
    _name = 'casso.transaction.wizard'
    _description = 'Casso Transaction Detail Wizard'

    transaction_id = fields.Char(string='Transaction ID')
    tid = fields.Char(string='TID')
    description = fields.Text(string='Description')
    amount = fields.Float(string='Amount')
    cusum_balance = fields.Float(string='Cusum Balance')
    when = fields.Datetime(string='Transaction Date')
    bank_sub_acc_id = fields.Char(string='Bank Sub Account ID')

