# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class DayLabor(models.Model):
    _name = 'day.labor'
    _description = 'Day Labor'
    _rec_name = 'name'
    
    name = fields.Char('Name')
    day_labor_coefficient = fields.Float('Day Labor Coefficient')
    unit_price = fields.Float('Unit Price')
    employee_applicable_ids = fields.Many2many('hr.employee',string="Employee Applicable")