# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ConfigTeleSale(models.Model):
	_name = 'config.telesale'
	_description = 'Config TeleSale'
	_rec_name = 'target'

	target = fields.Char('Target')
	code = fields.Char('Code')
	kpi_item_ids = fields.Many2many('kpi.item',string="KPI")
	employee_ids = fields.Many2many('hr.employee',string="Employee")
	line_ids = fields.One2many('config.telesale.line','config_id','Table')
	kpi_workload_ids = fields.One2many('kpi.workload','config_id','Table')
	stt = fields.Integer('STT')
	standard_tl = fields.Float('Standard TL')
	standard_points = fields.Float('Standard Points')
	currency_id = fields.Many2one('res.currency',string='Currency', related='company_id.currency_id')
	company_id = fields.Many2one('res.company',string='Company', default=lambda self: self.env.company)
	how_to_calculate = fields.Selection([('config_telesale','KPI TeleSale'),('kpi_workload','Management KPI')],string='How to calculate')
	total_indicator_ids = fields.Many2many('config.telesale','rel_config_telesale','total_indicator_id','config_id',string="Total Indicators")
	note = fields.Text('Note')
	calculate_kpis_by = fields.Selection([('by_output','By Output'),('by_revenue','By Revenue'),('actual_score','Actual score'),('by_bonus','Hoa hồng')],string="Calculate KPIs by")
	configure_related_output_kpis = fields.Many2one('config.telesale',string='Configure Related Output KPIs')
	calculate_the_amount_earned = fields.Selection([('config_telesale','Config TeleSale'),('ct_salary','CT Salary')],string='Calculate the amount earned')

	@api.onchange('how_to_calculate')
	def _change_how_to_calculate(self):
		for res in self:
			if res.how_to_calculate:
				res.code = 'LKPIDSHH' if res.how_to_calculate == 'config_telesale' else 'LKPIKLCV'

class ConfigTeleSaleLine(models.Model):
	_name = 'config.telesale.line'
	_description = 'Config TeleSale Line'

	config_id = fields.Many2one('config.telesale')
	value = fields.Float('Value')
	compare = fields.Selection([
		('greate_than','Greate Than'),
		('greater_than_or_equal_to','Greater than or equal to'),
		('smaller_than','Smaller Than'),
		('smaller_than_or_equal_to','Smaller than or equal to'),
		],string="Compare")
	achieved_money = fields.Monetary('Achieved money',currency_field='company_currency_id')
	company_currency_id = fields.Many2one('res.currency', string='Company Currency', compute='_compute_company_currency_id')
	
	@api.depends('config_id.company_id.currency_id')
	def _compute_company_currency_id(self):
		for r in self:
			r.company_currency_id = r.config_id.company_id.currency_id if r.config_id.company_id.currency_id else self.env.user.company_id.currency_id

class KPIWorkload(models.Model):
	_name = 'kpi.workload'
	_description = 'KPI Workload'

	config_id = fields.Many2one('config.telesale')
	value = fields.Float('Value')
	achieved_money = fields.Float('Achieved money')
