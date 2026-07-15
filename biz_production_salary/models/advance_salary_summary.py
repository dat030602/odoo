# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime,timedelta

class AdvanceSalarySummary(models.Model):
	_name = 'advance.salary.summary'
	_description = 'Tổng hợp tạm ứng lương theo ngày công'

	name = fields.Char(string="Tên phiếu", required=True)
	month = fields.Selection(
		[(str(i), 'Tháng %s' % i) for i in range(1, 13)],
		string="Tháng",
		required=True
	)
	year = fields.Selection(
		[(str(y), str(y)) for y in range(2020, 2101)],
		string="Năm",
		required=True,
		default=lambda self: str(datetime.now().year)
	)
	advance_date = fields.Integer(string="Ngày tạm ứng", required=True, default=18)
	payroll_type = fields.Selection([('office', 'Lương văn phòng'), ('production', 'Lương sản xuất')], string="Loại lương", default='office')
	standard_working_days_default = fields.Float(string="Ngày công chuẩn (mặc định)", default=26.0)
	department_id = fields.Many2one('hr.department', string="Phòng ban")
	line_ids = fields.One2many('advance.salary.line', 'advance_id', string="Chi tiết tạm ứng")
	state = fields.Selection(
		[('draft', 'Nháp'), ('lock', 'Đã khóa')],
		string="Trạng thái",
		default='draft'
	)
	currency_id = fields.Many2one('res.currency', string="Tiền tệ", default=lambda self: self.env.company.currency_id)
	total_amount = fields.Monetary(string="Tổng tạm ứng", compute="_compute_total_amount", store=True, currency_field='currency_id')

	@api.depends('line_ids.amount')
	def _compute_total_amount(self):
		for record in self:
			record.total_amount = sum(line.amount for line in record.line_ids)
	
	def action_compute_advance(self):
		for record in self:
			if record.payroll_type == 'office':
				record.line_ids.unlink()
				domain = [('state', '=', 'open')]
				if record.department_id:
					domain.append(('department_id', '=', record.department_id.id))
				
				contracts = self.env['hr.contract'].search(domain)
				lines = []
				for contract in contracts:
					emp = contract.employee_id
					# Lấy dữ liệu ngày công từ hr.working.day.import
					workdays_import = self.env['hr.working.day.import'].search([
						('update_id.month', '=', record.month),
						('update_id.year', '=', record.year),
						('employee_id', '=', emp.id)
					])
					
					actual_days = sum(wd.day_type_1 for wd in workdays_import)
					
					# Lấy ngày công chuẩn từ cột 5 của file import, nếu không có thì lấy mặc định
					imported_standard_days = sum(wd.day_type_5 for wd in workdays_import)
					emp_standard_days = imported_standard_days if imported_standard_days > 0 else record.standard_working_days_default
					
					if actual_days > 0 and emp_standard_days > 0:
						base_wage = contract.kpi_salary or contract.wage
						raw_amount = base_wage * 0.4 * (actual_days / emp_standard_days)
						amount = int(raw_amount / 100000) * 100000
						lines.append((0, 0, {
							'employee_id': emp.id,
							'wage': base_wage,
							'standard_working_days': emp_standard_days,
							'actual_working_days': actual_days,
							'amount': amount,
						}))
				
				if lines:
					record.write({'line_ids': lines})
	
	def action_lock(self):
		self.state = 'lock'
	
	def action_unlock(self):
		self.state = 'draft'

class AdvanceSalaryLine(models.Model):
	_name = 'advance.salary.line'
	_description = 'Chi tiết tạm ứng lương'

	advance_id = fields.Many2one('advance.salary.summary', string="Phiếu tạm ứng", ondelete='cascade')
	employee_id = fields.Many2one('hr.employee', string="Nhân viên", required=True)
	employee_code = fields.Char(string="Mã NV", related='employee_id.code', store=True)
	bank_account_number = fields.Char(string="Số TK", related='employee_id.bank_account_id.acc_number', store=True)
	bank_name = fields.Char(string="Ngân hàng", related='employee_id.bank_account_id.bank_id.name', store=True)
	wage = fields.Monetary(string="Mức lương", currency_field='currency_id')
	standard_working_days = fields.Float(string="Ngày công chuẩn")
	actual_working_days = fields.Float(string="Ngày làm việc")
	amount = fields.Monetary(string="Số tiền tạm ứng", required=True, currency_field='currency_id')
	currency_id = fields.Many2one('res.currency', string="Đơn vị tiền tệ", default=lambda self: self.env.company.currency_id)
 
