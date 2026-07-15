# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountAccount(models.Model):
    _inherit = 'account.account'

    partner_bank_id = fields.Many2one('res.partner.bank', string="Tài khoản ngân hàng")
