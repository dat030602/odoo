# -*- coding: utf-8 -*-
from odoo import api, fields, models

class TotalAmountReceivedByDay(models.Model):
	_name = 'total.amount.received.byday'
	_description = 'Total amount received by day'
	_order = 'summary_id,production_date,employee_id'

	summary_id = fields.Many2one('summary.output.daily.work', ondelete='cascade')
	production_date = fields.Date('Production date')
	employee_id = fields.Many2one('hr.employee','Employee')
	position_id = fields.Many2one(related='employee_id.job_id',string='Position')
	amount_received = fields.Monetary('Amount received', compute='_compute_amount_received', store=True)
	currency_id = fields.Many2one(related='summary_id.currency_id',string="Currency")

	@api.depends('summary_id.line_ids.employee_enjoys_ids.amount_1_person','summary_id.line_ids.employee_enjoys_ids.date','employee_id', 'production_date')
	def _compute_amount_received(self):
		for res in self:
			if res.summary_id.line_ids:
				enjoy_ids = res.summary_id.line_ids.employee_enjoys_ids.filtered(lambda x: x.employee_id == res.employee_id and res.production_date == x.date)
				res.amount_received = sum(enjoy_ids.mapped('amount_1_person'))
			else:
				res.amount_received = 0

