# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.fields import Command

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'
    
    total = fields.Float(compute='_compute_total', string='Tổng', store=True, digits=(16,3))
    amount = fields.Float(string='Số tiền', digits=(16,3))
