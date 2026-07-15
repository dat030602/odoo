# -*- coding: utf-8 -*-

from odoo import api, fields, models,_

class AccountPayment(models.Model):
	_inherit = 'account.payment'

	reconciliation_account_id = fields.Many2one("account.account", 'Reconciliation account')

	def action_post(self):
		if self.reconciliation_account_id:
			for line in self.line_ids:
				if line.debit > 0 and self.payment_type == 'outbound':
					line.account_id = self.reconciliation_account_id.id

				if line.credit > 0 and self.payment_type == 'inbound':
					line.account_id = self.reconciliation_account_id.id

		return super(AccountPayment, self).action_post()