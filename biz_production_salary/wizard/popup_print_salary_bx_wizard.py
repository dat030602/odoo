# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta, date

class PopupPrintSalaryBXWizard(models.TransientModel):
	_name = 'popup.print.salary.bx.wizard'
	_description = 'Popup Print Salary BX Wizard'

	month = fields.Selection([
		('01','Month 1'),('02','Month 2'),('03','Month 3'),
		('04','Month 4'),('05','Month 5'),('06','Month 6'),
		('07','Month 7'),('08','Month 8'),('09','Month 9'),
		('10','Month 10'),('11','Month 11'),('12','Month 12')],
		string='Month',required=True)
	year = fields.Char('Year',size=4, default=date.today().year,required=True)
	department_ids = fields.Many2many('hr.department',string="Departments",required=True)
	founder_id = fields.Many2one('hr.employee','Founder')
	hcns_department_id = fields.Many2one('hr.employee','HCNS Department')
	tckt_department_id = fields.Many2one('hr.employee','TCKT Department')
	unit_head_id = fields.Many2one('hr.employee','Unit Head')

	def action_print_excel(self):
		return self.env.ref('biz_production_salary.action_report_salary_bx_xlsx').report_action(self)