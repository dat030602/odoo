# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class EmployeeClassification(models.Model):
	_name = 'employee.classification'
	_description = 'Employee Classification'

	date = fields.Date('Date')
	employee_ids = fields.Many2many('hr.employee',string='Employees')
	classification_id = fields.Many2one('config.classification',string="Classification")
	proportion = fields.Float('Proportion')

	def name_get(self):
		result = []
		for inv in self:
			result.append((inv.id, _("Classification")))
		return result

	@api.onchange('classification_id')
	def _onchange_classification_id(self):
		for res in self:
			res.proportion = res.classification_id.proportion if res.classification_id else False

	def push_up_contract(self):
		HrAllowance = self.env['hr.allowance'].sudo()
		HrContract = self.env['hr.contract'].sudo()
		for line in self.employee_ids:
			contracts = HrContract.search([('employee_id','=',line.id),('state','=','open')])
			#xóa dòng trong bảng phụ cấp tháng trước
			for contract in contracts:
				year = int(self.date.strftime('%Y'))
				month = str(int(self.date.strftime('%m')))
				allowance_month = contract.allowance_month_ids.filtered(lambda x: x.year == year\
				 and x.month == month and x.code == 'TL')
				if allowance_month:
					allowance_month.unlink()
				allowance_id = HrAllowance.search([('name','=', 'Tỷ lệ'),('code','=','TL')],limit=1)
				if not allowance_id:
					allowance_id = HrAllowance.create({'name': 'Tỷ lệ','code': 'TL','is_fixed': True})
				v = {'amount': self.proportion, 'allowance_id': allowance_id.id, 'year': year, 'month': month, 'code': 'TL'}
				contract.allowance_month_ids = [(0,0,v)]