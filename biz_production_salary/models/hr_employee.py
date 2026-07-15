# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    worker_coefficient = fields.Float('Worker coefficient')
    
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    worker_coefficient = fields.Float('Worker coefficient')