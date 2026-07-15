# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, date, timedelta

class HrContract(models.Model):
	_inherit = 'hr.contract'

	kpi_salary = fields.Float('KPI Salary')
	insurance_salary = fields.Float('Insurance salary')
	wage = fields.Monetary('Basic salary')