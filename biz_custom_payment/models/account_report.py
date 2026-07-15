# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError

class AccountReport(models.Model):
	_inherit = 'account.report'

	@api.model
	def _format_aml_name(self, line_name, move_ref, move_name=None):
		if line_name and move_ref and line_name == move_ref:
			line_name = ''
		return super(AccountReport,self)._format_aml_name(line_name,move_ref,move_name=move_name)