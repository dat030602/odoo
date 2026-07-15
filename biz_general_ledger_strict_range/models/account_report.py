# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, osv, _lt


class AccountReport(models.Model):
	_inherit = 'account.report'

	def _init_options_custom(self, options, previous_options=None):
		super(AccountReport, self)._init_options_custom(options, previous_options=previous_options)
		# options['general_ledger_strict_range'] = True
		options['include_current_year_in_unaff_earnings'] = True

class GeneralLedgerCustomHandler(models.AbstractModel):
	_inherit = 'account.general.ledger.report.handler'

	def _get_options_initial_balance(self, options):
		new_options = super(GeneralLedgerCustomHandler, self)._get_options_initial_balance(options)

		new_options['include_current_year_in_unaff_earnings'] = True
		return new_options