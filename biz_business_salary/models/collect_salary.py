# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class CollectSalary(models.Model):
	_name = 'collect.salary'
	_description = 'Collect Salary'

	employee_id = fields.Many2one('hr.employee', 'Employee')
	date_from = fields.Date('Date From', required=True)
	date_to = fields.Date('Date To', required=True)
	state = fields.Selection([('draft','Draft'),('closed','Closed')], string='State', default="draft")
	line_ids = fields.One2many('collect.salary.line','collect_salary_id', string="Table")

	@api.depends('date_to','date_from','employee_id')
	def _compute_display_name(self):
		for record in self:
			def format_date(date):
				if not date:
					return ''
				return date.strftime('%d/%m/%Y')

			section_name = "%s-%s" % (format_date(record.date_from), format_date(record.date_to))
			if record.employee_id:
				section_name += ' %s' % record.employee_id.display_name
			record.display_name = section_name

	def action_open(self):
		self.state = 'draft'

	def action_close(self):
		self.state = 'closed'

	def action_synthetic(self):
		self.line_ids.unlink()
		ConfigTeleSale = self.env['config.telesale'].sudo()
		KpiScoreLine = self.env['kpi.scorecard.line'].sudo()
		HrContract = self.env['hr.contract'].sudo()

		domain_config = [('employee_ids','!=',False)]
		if self.employee_id:
			domain_config += [('employee_ids','=',self.employee_id.id)]
		data_config =  ConfigTeleSale.search(domain_config)
		#tính toán
		def calculate(d_config,empl,contract):
			result_1 = d_config.standard_tl
			result_2 = d_config.standard_points
			result_3 = 0
			#try catch divide
			def try_float_zero(a,b):
				try:
					return a/b
				except ZeroDivisionError:
					return 0

			def search_kpi(kpi_item_ids):
				domain_cal = [('period_id.date_start','>=',self.date_from),('period_id.date_end','<=',self.date_to),\
				('kpi_id','in',kpi_item_ids)]
				return KpiScoreLine.search(domain_cal)
			
			#return nếu có cấu hình total_indicator_ids
			if d_config.total_indicator_ids:
				search_line_created = self.line_ids.filtered(lambda x: x.content_id.id in d_config.total_indicator_ids.ids)
				result_1 = sum(search_line_created.mapped('standard_tl'))
				result_2 = sum(search_line_created.mapped('standard_points'))
				result_3 = sum(search_line_created.mapped('achieved_points'))
				return result_1,result_2,result_3
			
			#return nếu kh cấu hình kpi_item_ids
			if not d_config.kpi_item_ids:
				return result_1,result_2,result_3

			kpi_line = search_kpi(d_config.kpi_item_ids.ids)
			result_ = sum(kpi_line.mapped('actual_value')) if kpi_line else 0
			result_3 = result_

			return result_1,result_2,result_3

		def create_line(data):
			vals = []
			employees = data.employee_ids.ids if not self.employee_id else data.employee_ids.filtered(lambda x: self.employee_id == x).ids
			for empl in employees:
				contract = HrContract.search([('employee_id','=',empl),('state','=','open')],order="id desc",limit=1)
				standard_tl, standard_points, achieved_points = calculate(data,empl,contract)
				vals.append({
						'content_id': data.id,
						'standard_tl': standard_tl,
						'standard_points': standard_points,
						'achieved_points': achieved_points,
						'employee_id': empl
					})
			self.line_ids = [(0,0,v) for v in vals]

		#tính các cấu hình kh đc cấu hình total_indicator_ids trước
		for data_cf in data_config.filtered(lambda x: not x.total_indicator_ids):
			create_line(data_cf)
		#sau đó đi vào các cấu hình đc cấu hình total_indicator_ids để sum các giá trị đã tạo ra trc đó
		for data_cf in data_config.filtered(lambda x: x.total_indicator_ids):
			create_line(data_cf)

	def salary_calculation(self):
		HrContract = self.env['hr.contract'].sudo()
		HrAllowance = self.env['hr.allowance'].sudo()
		year = int(self.date_to.strftime('%Y'))
		month = str(int(self.date_to.strftime('%m')))
		#chỉ tìm và đẩy các dòng có cấu hình mã qua hợp đồng
		line_ids = self.line_ids.filtered(lambda x: x.content_id and x.content_id.code)

		if not line_ids:
			return

		# Nhóm theo employee_id và code để tổng hợp số tiền
		employee_code_results = {}
		for line in line_ids:
			key = (line.employee_id.id, line.content_id.code)
			if key not in employee_code_results:
				employee_code_results[key] = {
					'employee_id': line.employee_id.id,
					'code': line.content_id.code,
					'name': line.content_id.target,
					'total_amount': 0
				}
			employee_code_results[key]['total_amount'] += line.achieved_amount

		# Đẩy theo số tổng cho từng nhân viên và code
		for key, result in employee_code_results.items():
			employee_id = result['employee_id']
			code = result['code']
			name = result['name']
			total_amount = result['total_amount']
			
			contracts = HrContract.search([('employee_id','=',employee_id),('state','=','open')])
			
			for contract in contracts:
				# Xóa dòng trong bảng phụ cấp tháng trước
				allowance_month = contract.allowance_month_ids.filtered(lambda x: x.year == year and x.month == month and x.code == code)
				if allowance_month:
					allowance_month.unlink()
				
				# Tạo allowance nếu chưa có
				allowance_id = HrAllowance.search([('code','=',code)])
				if not allowance_id:
					allowance_id = HrAllowance.create({'name': name,'code': code,'is_fixed': False})
				
				# Tạo allowance_month với số tiền đã tổng hợp
				v = {'amount': total_amount, 'allowance_id': allowance_id.id, 'year': year, 'month': month, 'code': code}
				contract.allowance_month_ids = [(0,0,v)]



class CollectSalaryLine(models.Model):
	_name = 'collect.salary.line'
	_description = 'Collect Salary Line'
	_order = "stt"

	collect_salary_id = fields.Many2one('collect.salary')
	employee_id = fields.Many2one('hr.employee',string='Employee')
	content_id = fields.Many2one('config.telesale',string='Content')
	stt = fields.Integer(related='content_id.stt', store=True)
	standard_tl = fields.Float('Standard TL', digits=(16, 4))
	standard_points = fields.Float('Standard Points')
	standard_amount = fields.Monetary('Standard Amount',currency_field='currency_id', compute='_compute_all')
	achieved_tl = fields.Float('Achieved TL', compute='_compute_all', digits=(16, 4))
	achieved_points = fields.Float('Achieved Points')
	achieved_amount = fields.Monetary('Achieved Amount',currency_field='currency_id', compute='_compute_all')
	currency_id = fields.Many2one('res.currency',string='Currency', related='content_id.currency_id')
	note = fields.Text('Note')
	is_over = fields.Boolean('Có thể vượt')

	@api.depends(
		'achieved_points',
		'standard_points',
		'content_id.total_indicator_ids',
		'standard_tl',
		'employee_id',
		'standard_amount',
		'is_over',
		'collect_salary_id.line_ids'
	)
	def _compute_all(self):
		for record in self:
			# Compute standard_amount
			record.standard_amount = record.standard_tl * (record.employee_id.contract_id.kpi_salary if record.employee_id and record.employee_id.contract_id else 0.0)

			# Compute achieved_tl
			if record.content_id.total_indicator_ids or record.content_id.calculate_kpis_by == 'actual_score':
				record.achieved_tl = 1
			else:
				record.achieved_tl = record.achieved_points / (record.standard_points or 1)

			# Compute achieved_amount
			if record.content_id.total_indicator_ids:
				total_indicator_ids = record.content_id.total_indicator_ids
				search_line_created = record.collect_salary_id.line_ids.filtered(lambda x: x.content_id in total_indicator_ids)
				amount_sum = sum(search_line_created.mapped('achieved_amount'))
				record.achieved_amount = amount_sum
			elif record.content_id.calculate_kpis_by == 'actual_score':
				record.achieved_amount = record.achieved_points
			else:
				rate = record.achieved_tl
				if not record.is_over and rate:
					rate = 1
				record.achieved_amount = record.standard_amount * rate
