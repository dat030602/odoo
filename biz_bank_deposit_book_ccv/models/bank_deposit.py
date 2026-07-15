from odoo import models, api, fields, _

from odoo.exceptions import ValidationError

class BankDepositBook(models.TransientModel):
	_inherit = 'bank.deposit.book'

	creator_id = fields.Many2one("res.users", 'Vote Creator')
	chief_id = fields.Many2one("res.users", 'Chief Accounting Officer')
	unit_head_id = fields.Many2one("res.users", 'Unit head')

	type_print = fields.Selection([
			('vnd','VND'),
			('usd','USD')
		],  default='vnd')