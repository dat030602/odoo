# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountAcount(models.Model):
    _inherit = 'account.account'

    is_compare = fields.Boolean('Reconcilation Inventory and Ledgers')