# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from datetime import datetime, timedelta, date
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.misc import formatLang
import odoo.addons.decimal_precision as dp
import time

SELECTION_MONTH = [('1','January'),('2','February'),('3','March'),('4','April'),
                              ('5','May'),('6','June'),('7','July'),('8','August'),
                              ('9','September'),('10','October'),('11','November'),('12','December')]

class hr_contract_workday(models.Model):
    _name = 'hr.contract.workday'
    _description = 'Contract workday'
    
    name = fields.Char('Name')
    code = fields.Char('Code')
    contract_id = fields.Many2one('hr.contract', string='Contract', ondelete='cascade')
    month = fields.Selection(SELECTION_MONTH, 'Month', default=date.today().month)
    year = fields.Char('Year', size=4, default=date.today().year)
    totay_days = fields.Float('Total days')
    totay_hours = fields.Float('Total hours')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    date_time = fields.Datetime('Datetime')


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def _default_allowance_fix(self):
        value = []
        active_ids = self.env['hr.allowance'].search([('is_fixed', '=', True)])
        for allowance in active_ids:
            allowance_fix = {
                'allowance_id': allowance.id,
                'name': allowance.name,
                'code': allowance.code,
                'amount': allowance.amount,
            }
            value.append((0, 0, allowance_fix))
        return value
    
    @api.model
    def _default_deduction_fix(self):
        value = []
        active_ids = self.env['hr.deduction'].search([('is_fixed', '=', True)])
        for deduction in active_ids:
            deduction_fix = {
                'deduction_id': deduction.id,
                'name': deduction.name,
                'code': deduction.code,
                'amount': deduction.amount,
            }
            value.append((0, 0, deduction_fix))
        return value
    
    allowance_fix_ids = fields.One2many('hr.payroll.allowance.fixed', 'contract_id', string='Fixed Allowances', default=_default_allowance_fix)
    allowance_month_ids = fields.One2many('hr.payroll.allowance.monthly', 'contract_id', string='Monthly Allowances',readonly =True)
    deduction_fix_ids = fields.One2many('hr.payroll.deduction.fixed', 'contract_id', string='Fixed Deductible', default=_default_deduction_fix)
    deduction_month_ids = fields.One2many('hr.payroll.deduction.monthly', 'contract_id', string='Monthly Deductible',readonly =True)
    workday_ids = fields.One2many('hr.contract.workday', 'contract_id', 'Workday',readonly =True)
    probation_date = fields.Date('Probation Date')
    probation_end_date = fields.Date('Probation End Date')
