# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api,_
from odoo.exceptions import UserError,ValidationError

class AccountTax(models.Model):
	_inherit = 'account.tax'

	not_taxable = fields.Boolean("Not taxable")
	not_declared_paid = fields.Boolean("Not declared/paid")

	@api.model_create_multi
	def create(self, vals_list):
		for vals  in vals_list:
			if vals.get("not_taxable", False) or vals.get("not_declared_paid"):
				if vals.get("not_taxable", False) == True and vals.get("not_declared_paid", False) == True:
					raise ValidationError(_('A tax cannot be both Non-Taxable and Non-Declarable/Payable.'))

		return super(AccountTax, self).create(vals_list)

	def write(self, vals):
		if vals.get("not_taxable", False) or vals.get("not_declared_paid"):
			not_taxable = vals.get('not_taxable', False) or self.not_taxable
			not_declared_paid = vals.get('not_declared_paid', False) or self.not_declared_paid

			if not_taxable == True and not_declared_paid == True:
				raise ValidationError(_('A tax cannot be both Non-Taxable and Non-Declarable/Payable.'))

		return super(AccountTax, self).write(vals)
