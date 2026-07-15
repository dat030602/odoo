# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _, osv

class AccountReport(models.Model):
	_inherit = 'account.report'

	filter_account = fields.Boolean('Filter account')

	def _get_options_domain(self, options, date_scope):
		domain = super(AccountReport, self)._get_options_domain(options, date_scope)
		domain += self._get_options_acount_domain(options)
		return domain

	@api.model
	def _get_options_acount_domain(self, options):
		domain = []
		if options.get('account_ids'):
			account_ids = [int(account) for account in options['account_ids']]
			account_domain = [('id', 'in', account_ids),('company_id','in', [False, self.env.company.id])]
			selected_accounts = self.env['account.account'].search(account_domain)
			if selected_accounts:
				domain.append(('account_id', 'in', selected_accounts.ids))

		return domain

	def _init_options_account(self, options, previous_options=None):
		if not self.filter_account:
			return

		options['account'] = True
		previous_domain = [
			('id','in', previous_options.get('account_ids')),
			('company_id','in', [False, self.env.company.id])
		]
		account_ids = self.env['account.account'].search(previous_domain)
		options['account_ids'] = account_ids.ids
		selected_account_ids = [int(account) for account in options['account_ids']]
		domain = [
			('id','in', selected_account_ids),
			('company_id','in', [False, self.env.company.id])
		]
		selected_accounts = selected_account_ids and self.env['account.account'].search(domain) or self.env['account.account']
		options['selected_account_ids'] = selected_accounts.mapped('name')