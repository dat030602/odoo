# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    internal_account_id = fields.Many2one("alpha.internal.account")
