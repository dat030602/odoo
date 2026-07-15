# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ChangeManualWorkerCoefficientByDay(models.Model):
    _name = 'change.manual.worker.coefficient.byday'
    _description = 'Change Manual Worker Coefficient By Day'

    date = fields.Date('Date')
    employee_ids = fields.Many2many('hr.employee',string='Employees')
    coefficient = fields.Float('Coefficient')