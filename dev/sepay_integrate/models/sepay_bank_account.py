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

    account_id = fields.Char(string='Account ID')
    account_holder_name = fields.Char(string='Account Holder Name')
    account_number = fields.Char(string='Account Number', required=True)
    last_transaction = fields.Datetime(string='Last Transaction Date')
    label = fields.Char(string='Label')
    active = fields.Boolean(string='Active', default=True)
    created_at = fields.Datetime(string='Created At')
    bank_short_name = fields.Char(string='Bank Short Name')
    bank_full_name = fields.Char(string='Bank Full Name')
    bank_bin = fields.Char(string='Bank BIN')
    bank_code = fields.Char(string='Bank Code')
    journal_id = fields.Many2one('account.journal', string='Journal')

    # Bank reference
    bank_id = fields.Many2one('vietqr.bank.config', string='Bank', compute='_compute_bank_id', store=True)
    bank_sepay_id = fields.Many2one('sepay.bank', string='Sepay Bank Account')

    @api.depends('account_number', 'bank_short_name', 'account_holder_name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.account_number} - {record.bank_short_name} - {record.account_holder_name}"

    @api.depends('bank_code')
    def _compute_bank_id(self):
        for record in self:
            bank = self.env['vietqr.bank.config'].search([('code', 'ilike', record.bank_code)], limit=1)
            record.bank_id = bank.id if bank else False

    def action_create_account_bank(self):
        self.ensure_one()
        if not self.bank_id:
            raise UserError(_('No matching Bank found for CODE: %s') % self.bank_code)
        existing_bank_account = self.env['sepay.bank'].search([('sepay_id', '=', self.id)], limit=1)
        if existing_bank_account:
            raise UserError(_('Bank account with number %s and bank %s already exists.') % (self.account_number, self.bank_id.name))
        partner_bank_id = self.env['res.partner.bank'].search([('acc_number', '=', self.account_number)], limit=1)
        bank_id = self.env['res.bank'].search([('bic', '=', self.bank_id.code)], limit=1)
        if not partner_bank_id:
            partner_bank_id = self.env['res.partner.bank'].create({
                'acc_number': self.account_number,
                'bank_id': bank_id.id,
                'partner_id': self.env.company.partner_id.id,
            })
        bank_account = self.env['sepay.bank'].create({
            'name': self.display_name,
            'sepay_id': self.id,
            'template': 'compact',
            'partner_bank_id': partner_bank_id.id,
            'sepay_bank_id': self.bank_id.id,
        })
        self.bank_sepay_id = bank_account
        return bank_account
