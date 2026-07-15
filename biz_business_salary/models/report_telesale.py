from odoo import models, fields, api, _
import heapq
import logging
_logger = logging.getLogger(__name__)

class ReportTeleSale(models.Model):
	_name = 'report.telesale'
	_description = 'Report TeleSale'

	employee_id = fields.Many2one('hr.employee',string="Employee")
	date_from = fields.Date('Date From')
	date_to = fields.Date('Date To')
	line_ids = fields.One2many('report.telesale.line','report_id','Table')
	sum_bonus_ids = fields.One2many('sum.bonus','report_id','Table')

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

	def action_kpi_summary(self):
		for rec in self:
			rec.line_ids.unlink()
			rec.sum_bonus_ids.unlink()
			# config = self.env['config.telesale'].search([('how_to_calculate','=','config_telesale')])
			HrContract = self.env['hr.contract'].sudo()
			def calculate(kpi):
				domain_cal = [('period_id.date_start','=',rec.date_from),('period_id.date_end','=',rec.date_to),\
					('kpi_id','=',kpi.id),('employee_id','=',kpi.employee_id.id)]
				kpi_scorecard_line = self.env['kpi.scorecard.line'].search(domain_cal)
				return kpi_scorecard_line

			def compare_table_config(conf,value):
				def closest(lst, K):
					return heapq.nsmallest(1, lst, key=lambda x: abs(x-K))[0]

				dk1 = conf.line_ids.filtered(lambda x: x.value == value and x.compare in ['greater_than_or_equal_to','smaller_than_or_equal_to'])
				if dk1:
					value = closest(dk1.mapped('value'),value)
					return dk1.filtered(lambda x: x.value == value)[0].achieved_money
				dk2 = conf.line_ids.filtered(lambda x: x.value < value and x.compare in ['greater_than_or_equal_to','greate_than'])
				if dk2:
					value = closest(dk2.mapped('value'),value)
					return dk2.filtered(lambda x: x.value == value)[0].achieved_money
				dk3 = conf.line_ids.filtered(lambda x: x.value > value and x.compare in ['smaller_than','smaller_than_or_equal_to'])
				if dk3:
					value = closest(dk3.mapped('value'),value)
					return dk3.filtered(lambda x: x.value == value)[0].achieved_money
				return 0

			kpi_scorecard_ids = self.env['kpi.scorecard.line'].search([('period_id.date_start','=',rec.date_from),('period_id.date_end','=',rec.date_to),('employee_id','=',rec.employee_id.id)])
			employee = {}
			for kpi_scorecard_id in kpi_scorecard_ids:
				kpi = kpi_scorecard_id.kpi_id
				kpi_scorecard_id._action_create_kpi_config()
				if not kpi_scorecard_id.kpi_config_id:
					kpi_scorecard_id._compute_kpi_config_id()
				conf = kpi_scorecard_id.kpi_config_id
				performed = sum(kpi_scorecard_id.mapped('actual_value'))
				plan = sum(kpi_scorecard_id.mapped('target_value'))
				achieved_money = 0

				if conf.calculate_the_amount_earned == 'config_telesale':
					achieved_money = compare_table_config(conf,performed)
				if conf.calculate_the_amount_earned == 'ct_salary':
					contract = HrContract.search([('employee_id','=',kpi.employee_id.id),('state','=','open')],order="id desc",limit=1)
					if contract:
						try:
							achieved_money = contract.wage/plan*performed
						except ZeroDivisionError:
							achieved_money = 0

				if not kpi.employee_id.id in employee:
					employee[kpi.employee_id.id] = achieved_money
				else:
					employee[kpi.employee_id.id] += achieved_money
				val = {
					'target_id': conf.id,
					'performed': performed,
					'plan': plan,
					'achieved_money': achieved_money,
					'employee_id': kpi.employee_id.id
				}
				if not rec.line_ids.filtered(lambda x: x.target_id == conf):
					rec.line_ids = [(0,0,val)]

			for k,v in employee.items():
				rec.sum_bonus_ids = [(0,0,{'employee_id': k,'total_bonus': v})]

	def salary_calculation(self):
		HrContract = self.env['hr.contract'].sudo()
		HrAllowance = self.env['hr.allowance'].sudo()
		year = int(self.date_to.strftime('%Y'))
		month = str(int(self.date_to.strftime('%m')))
		#chỉ tìm và đẩy các dòng có cấu hình mã qua hợp đồng
		line_ids = self.line_ids.filtered(lambda x: x.target_id and x.target_id.code)

		if not line_ids:
			return

		# Nhóm theo employee_id và code để tổng hợp số tiền
		employee_code_results = {}
		for line in line_ids:
			key = (line.employee_id.id, line.target_id.code)
			if key not in employee_code_results:
				employee_code_results[key] = {
					'employee_id': line.employee_id.id,
					'code': line.target_id.code,
					'name': line.target_id.target,
					'total_amount': 0
				}
			employee_code_results[key]['total_amount'] += line.achieved_money

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
					allowance_id = HrAllowance.create({'name': name,'code': code,'is_fixed': True})
				
				# Tạo allowance_month với số tiền đã tổng hợp
				v = {'amount': total_amount, 'allowance_id': allowance_id.id, 'year': year, 'month': month, 'code': code}
				contract.allowance_month_ids = [(0,0,v)]

					
	def export_to_excel(self):
		print('412412421')

class ConfigTeleSaleLine(models.Model):
	_name = 'report.telesale.line'
	_description = 'Report TeleSale Line'
	_order = 'stt'

	report_id = fields.Many2one('report.telesale')
	target_id = fields.Many2one('config.telesale',string='Target')
	stt = fields.Integer(related='target_id.stt', store=True)
	performed = fields.Float('Performed')
	plan = fields.Float('Plan')
	achi_rt_cp_to_plan = fields.Float('Achievement rate compared to plan', compute='_compute_achi_rt_cp_to_plan')
	achieved_money = fields.Monetary('Achieved money',currency_field='company_currency_id')
	company_currency_id = fields.Many2one('res.currency', string='Company Currency', compute='_compute_company_currency_id')
	note = fields.Text('Note')
	employee_id = fields.Many2one('hr.employee','Employee')

	@api.depends('employee_id.company_id.currency_id')
	def _compute_company_currency_id(self):
		for r in self:
			r.company_currency_id = r.employee_id.company_id.currency_id if r.employee_id.company_id.currency_id else self.env.user.company_id.currency_id
	
	@api.depends('performed', 'plan')
	def _compute_achi_rt_cp_to_plan(self):
		for r in self:
			r.achi_rt_cp_to_plan = r.performed / (r.plan or 1)

class SumBonus(models.Model):
	_name = 'sum.bonus'
	_description = 'Sum Bonus'

	report_id = fields.Many2one('report.telesale')
	employee_id = fields.Many2one('hr.employee','Employee')
	total_bonus = fields.Monetary('Total Bonus',currency_field='company_currency_id')
	company_currency_id = fields.Many2one('res.currency', string='Company Currency', compute='_compute_company_currency_id')

	@api.depends('employee_id.company_id.currency_id')
	def _compute_company_currency_id(self):
		for r in self:
			r.company_currency_id = r.employee_id.company_id.currency_id if r.employee_id.company_id.currency_id else self.env.user.company_id.currency_id

	