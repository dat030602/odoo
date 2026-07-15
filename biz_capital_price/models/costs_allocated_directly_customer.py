# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression
from datetime import timedelta, datetime, time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class CostsAllocatedDirectlyItems(models.Model):
	_name = 'costs.allocated.directly.items'
	_description = 'Costs allocated directly to items'
	_rec_name = 'date'

	date = fields.Date("Expense entry date")
	enter_cost_ids = fields.One2many("enter.costs.allocated", 'allocated_id', 'Enter cost')
	journal_id = fields.Many2one("account.journal", 'Journal')

	def action_confirm(self):
		for line in self.enter_cost_ids:
			credit_account_id = line.account_counterpart_id
			debit_account_id = line.product_id.categ_id.property_stock_valuation_account_id

			taxes = line.tax_id.compute_all(line.allocation_cost,quantity=1)
			balance = taxes['total_included']

			line_vals = {
				'name': line.product_id.name,
				'product_id': line.product_id.id,
				'quantity': 1,
				'product_uom_id': line.product_id.uom_id.id,
				'ref': line.product_id.name,
				'partner_id': line.partner_id.id,
			}

			move_lines = {
				'credit_line_vals': {
					**line_vals,
					'balance': -line.allocation_cost,
					'account_id': credit_account_id.id,
					'tax_ids': [(6,0, line.tax_id.ids)]
				},
				'debit_line_vals': {
					**line_vals,
					'balance': balance,
					'account_id': debit_account_id.id,
				},
			}
			vals = {
				'journal_id': self.journal_id.id,
				'line_ids': [(0,0, val) for val in move_lines.values()],
				'date': self.date,
				'invoice_date': self.date,
				'ref': line.product_id.name,
				'move_type': 'entry',
			}
			move_id = self.env['account.move'].create(vals)
			move_id.action_post()
			line.move_id = move_id.id		

class EnterCostsAllocated(models.Model):
	_name = 'enter.costs.allocated'	
	_description = 'Enter cost'

	allocated_id = fields.Many2one("costs.allocated.directly.items", 'Allocated', ondelete="cascade")
	allocation_cost = fields.Float("Allocation cost")
	partner_id = fields.Many2one("res.partner", 'Partner')
	product_id = fields.Many2one("product.product", 'Product')
	tax_id = fields.Many2one('account.tax', 'Tax', domain="[('type_tax_use','=', 'purchase')]")
	account_counterpart_id = fields.Many2one("account.account", 'Account counterpart')
	move_id = fields.Many2one("account.move", 'Entry')
