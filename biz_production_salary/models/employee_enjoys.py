# -*- coding: utf-8 -*-
from odoo import api, fields, models

class EmployeeEnjoys(models.Model):
	_name = 'employee.enjoys'
	_description = 'Employee enjoys'
	_order = 'summary_line_id,date,rate desc'

	summary_line_id = fields.Many2one('summary.output.spreadsheet', ondelete='cascade')
	date = fields.Date('Date')
	employee_id = fields.Many2one('hr.employee','Employee')
	rate = fields.Float('Rate')
	total_amount_1_person = fields.Monetary('Total Amount/1 person',related='summary_line_id.total_amount_1_person',store=True)
	amount_1_person = fields.Monetary('Amount/1 person',compute="_compute_amount_1_person",store=True)
	currency_id = fields.Many2one(related='summary_line_id.currency_id',string="Currency")

	@api.depends('rate','total_amount_1_person')
	def _compute_amount_1_person(self):
		for res in self:
			res.amount_1_person = res.rate * res.total_amount_1_person

