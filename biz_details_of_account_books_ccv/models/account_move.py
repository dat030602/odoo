# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMoveSales(models.Model):
    _inherit = 'account.move'

    note = fields.Char('Note')