# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class CassoTransactionWizard(models.TransientModel):
    _name = 'casso.transaction.wizard'
    _description = 'Casso Transaction Detail Wizard'

    casso_id = fields.Char(string='Casso ID')
    casso_reference = fields.Char(string='Reference')
    casso_description = fields.Char(string='Description')
    casso_amount = fields.Float(string='Amount')
    casso_transactionDateTime = fields.Datetime(string='Transaction Date Time')
    casso_accountNumber = fields.Char(string='Account Number')
    casso_bankName = fields.Char(string='Bank Name')
    casso_bankAbbreviation = fields.Char(string='Bank Abbreviation')
    casso_virtualAccountNumber = fields.Char(string='Virtual Account Number')
    casso_virtualAccountName = fields.Char(string='Virtual Account Name')
    casso_counterAccountName = fields.Char(string='Counterpart Account Name')
    casso_counterAccountNumber = fields.Char(string='Counterpart Account Number')
    casso_counterAccountBankId = fields.Char(string='Counterpart Account Bank ID')
    casso_counterAccountBankName = fields.Char(string='Counterpart Account Bank Name')
