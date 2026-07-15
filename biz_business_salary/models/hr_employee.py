# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, date, timedelta

class HrEmployee(models.Model):
	_inherit = 'hr.employee'

	children = fields.Integer(string='Number of Dependents')
	automatically_calculate_overtime = fields.Boolean('Automatically calculate overtime')
	default_enough_work = fields.Boolean('Default enough work')
	skip_timekeeping_machine = fields.Boolean('Skip timekeeping machine')
	is_manager_sales = fields.Boolean('Is manager')

class HrEmployeePublic(models.Model):
	_inherit = 'hr.employee.public'

	children = fields.Integer(string='Number of Dependents')
	automatically_calculate_overtime = fields.Boolean('Automatically calculate overtime')
	default_enough_work = fields.Boolean('Default enough work')
	skip_timekeeping_machine = fields.Boolean('Skip timekeeping machine')
	is_manager_sales = fields.Boolean('Is manager')
