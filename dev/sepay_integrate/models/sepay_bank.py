# -*- coding: utf-8 -*-
from odoo import models, fields

class SePayBank(models.Model):
    _inherit = 'sepay.bank'

    sepay_id = fields.Many2one('sepay.bank.account', string='Sepay Bank', compute='_compute_bank_id', store=True)
