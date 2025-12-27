# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import logging
import datetime

_logger = logging.getLogger(__name__)


class SePayBankAccount(models.Model):
    _name = 'sepay.bank.account'
    _description = 'SePay Bank Account'

    parent_id = fields.Many2one('sepay.config', string='Parent Config', required=True, ondelete='cascade')

    account_id = fields.Char(string='Account ID', readonly=True)
    account_holder_name = fields.Char(string='Account Holder Name', readonly=True)
    account_number = fields.Char(string='Account Number', required=True)
    last_transaction = fields.Datetime(string='Last Transaction Date', readonly=True)
    label = fields.Char(string='Label', readonly=True)
    active = fields.Boolean(string='Active', default=True)
    created_at = fields.Datetime(string='Created At', readonly=True)
    bank_short_name = fields.Char(string='Bank Short Name', readonly=True)
    bank_full_name = fields.Char(string='Bank Full Name', readonly=True)
    bank_bin = fields.Char(string='Bank BIN', readonly=True)
    bank_code = fields.Char(string='Bank Code', readonly=True)

    # Bank reference
    bank_id = fields.Many2one('vietqr.bank.config', string='Bank', compute='_compute_bank_id', store=True)

    @api.depends('account_number')
    def _compute_bank_id(self):
        """Match bank by brand name"""
        for record in self:
            if record.account_number:
                # Try to find bank by code or name
                bank = self.env['vietqr.bank.config'].search([('code', 'ilike', record.account_number)], limit=1)
                if not bank:
                    bank = self.env['vietqr.bank.config'].search([('name', 'ilike', record.account_number)], limit=1)
                record.bank_id = bank.id if bank else False
