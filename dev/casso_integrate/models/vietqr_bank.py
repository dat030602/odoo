# -*- coding: utf-8 -*-
from odoo import models, fields

class VietqrBank(models.Model):
    _inherit = 'vietqr.bank'

    casso_bank_id = fields.Many2one('casso.bank.account', string='Casso Bank')
