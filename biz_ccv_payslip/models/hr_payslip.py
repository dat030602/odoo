# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError

class HrPayslipRun(models.Model):
	_inherit = 'hr.payslip.run'

	working_days_per_month = fields.Float("Number of working days per month")

class HrPayslip(models.Model):
	_inherit = 'hr.payslip'

	employee_code = fields.Char(related='employee_id.code', string='Mã nhân viên', readonly=True, store=True)
	employee_pure_name = fields.Char(string='Họ và Tên', compute='_compute_employee_pure_name')
	bank_acc_number = fields.Char(related='employee_id.bank_account_id.acc_number', string='Số tài khoản', readonly=True, store=True)
	bank_id = fields.Many2one(related='employee_id.bank_account_id.bank_id', string='Ngân hàng', readonly=True, store=True)

	@api.depends('employee_id.name')
	def _compute_employee_pure_name(self):
		for rec in self:
			if rec.employee_id and rec.employee_id.name:
				parts = rec.employee_id.name.split(' - ')
				rec.employee_pure_name = parts[-1].strip() if parts else ''
			else:
				rec.employee_pure_name = ''

	@api.model
	def _search(self, domain, *args, **kwargs):
		if not self.env.su and not self.env.user.has_group('hr_payroll.group_hr_payroll_user'):
			domain = (domain or []) + [('state', 'in', ['done', 'paid'])]
		return super(HrPayslip, self)._search(domain, *args, **kwargs)

	def read(self, fields=None, load='_classic_read'):
		if not self.env.su and not self.env.user.has_group('hr_payroll.group_hr_payroll_user'):
			for slip in self:
				if slip.state not in ['done', 'paid']:
					raise AccessError(_("Bạn chỉ có thể xem phiếu lương khi trạng thái là Đã thanh toán."))
		return super(HrPayslip, self).read(fields=fields, load=load)

	@api.model
	def number_to_vietnamese_words(self, number):
		units = ['', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín']
		teens = ['', 'mười', 'hai mươi', 'ba mươi', 'bốn mươi', 'năm mươi', 'sáu mươi', 'bảy mươi', 'tám mươi', 'chín mươi']
		places = ['', 'nghìn', 'triệu', 'tỷ']

		if number == 0:
			return 'không đồng'

		def read_three_digits(num):
			result = ''
			hundreds = num // 100
			remainder = num % 100
			if hundreds > 0:
				result += units[hundreds] + ' trăm '
				if remainder < 10 and remainder > 0:
					result += 'lẻ '
			elif remainder > 0 and num < 1000 and number >= 1000:
				result += 'không trăm '
				if remainder < 10 and remainder > 0:
					result += 'lẻ '
			if remainder >= 10:
				result += teens[remainder // 10] + ' '
				if remainder % 10 > 0:
					result += units[remainder % 10] + ' '
			elif remainder > 0:
				result += units[remainder] + ' '
			return result.strip()

		if number < 0:
			return 'âm ' + self.number_to_vietnamese_words(-number)

		parts = []
		place_idx = 0
		while number > 0:
			chunk = number % 1000
			if chunk > 0:
				chunk_words = read_three_digits(chunk)
				if place_idx > 0:
					chunk_words += ' ' + places[place_idx]
				parts.append(chunk_words)
			number //= 1000
			place_idx += 1

		result = ' '.join(reversed(parts)).strip()
		# Clean up spaces
		import re
		result = re.sub(r'\s+', ' ', result).strip()
		return result + ' đồng'

class HrPayslipLine(models.Model):
	_inherit = 'hr.payslip.line'

	amount = fields.Float(digits=(16, 0))
	total = fields.Float(digits=(16, 0))