# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _

class AccountAccount(models.Model):
	_inherit = 'account.account'

	is_warehouse_account = fields.Boolean("Warehouse account")