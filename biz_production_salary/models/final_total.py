# -*- coding: utf-8 -*-
from odoo import api, fields, models

class FinalTotal(models.Model):
	_name = 'final.total'
	_description = 'Final total'
	_order = 'summary_id,employee_id'

	summary_id = fields.Many2one('summary.output.daily.work', ondelete='cascade')
	employee_id = fields.Many2one('hr.employee','Employee')
	amount_received = fields.Monetary('Amount received', compute='_compute_amount_received', store=True)
	currency_id = fields.Many2one(related='summary_id.currency_id',string="Currency")

	@api.depends('summary_id.line_1_ids.amount_received','summary_id.line_1_ids.employee_id','employee_id')
	def _compute_amount_received(self):
		for res in self:
			res.amount_received = sum(res.summary_id.line_1_ids.filtered(lambda x: x.employee_id == res.employee_id).mapped('amount_received'))

