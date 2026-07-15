# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta, date

SELECTION_MONTH = [('1','January'),('2','February'),('3','March'),('4','April'),
                              ('5','May'),('6','June'),('7','July'),('8','August'),
                              ('9','September'),('10','October'),('11','November'),('12','December')]

class HrDeductionImport(models.Model):
    _name = 'hr.deduction.import'
    _description = 'Column Import Allowances'
    
    name = fields.Char('Name')
    deduction_id = fields.Many2one('hr.deduction', string='Deduction', default=False)
    
    
class hr_deduction(models.Model):
    _name = 'hr.deduction'
    _description = 'Deduction'
    
    name = fields.Char('Deductible Name')
    code = fields.Char('Deductible Code')
    column_import = fields.Many2one('hr.deduction.import', string='Row number of import file')
    amount = fields.Float('Total')
    is_fixed = fields.Boolean('Fixed')
    
    @api.model_create_multi
    def create(self, vals):
        res = super(hr_deduction, self).create(vals)

        for deduction_obj in res: 
            if deduction_obj.column_import:
                deduction_obj.column_import.write({'deduction_id': deduction_obj.id})
        return res
    
    def write(self,vals):
        for record in self:
            if 'column_import' in vals:
                column_import = vals.get('column_import',False)
                if record.column_import:
                    column_obj = self.env['hr.deduction.import'].browse(record.column_import.id)
                    column_obj.write({'deduction_id':False})
                if column_import:
                    column_obj = self.env['hr.deduction.import'].browse(column_import)
                    column_obj.write({'deduction_id': record.id})
        return super(hr_deduction, self).write(vals)
    
    
    def unlink(self):
        for record in self:
            if record.column_import:
                column_obj = self.env['hr.deduction.import'].browse(record.column_import.id)
                column_obj.write({'deduction_id':False})
        return super(hr_deduction, self).unlink()


class hr_payroll_deduction_import(models.Model):
    _name = 'hr.payroll.deduction.import'
    _description = 'Payroll Deduction Import'
    
    employee_code = fields.Char('Employee Code')
    employee_id = fields.Many2one('hr.employee', string='Employee Name')
    contract_id = fields.Many2one('hr.contract', string='Contract')
    update_id = fields.Many2one('hr.payroll.update', string='Payroll Update')
    deduction_1 = fields.Float('Deduction 1')
    deduction_2 = fields.Float('Deduction 2')
    deduction_3 = fields.Float('Deduction 3')
    deduction_4 = fields.Float('Deduction 4')
    deduction_5 = fields.Float('Deduction 5')
    deduction_6 = fields.Float('Deduction 6')
    deduction_7 = fields.Float('Deduction 7')
    deduction_8 = fields.Float('Deduction 8')
    deduction_9 = fields.Float('Deduction 9')
    deduction_10 = fields.Float('Deduction 10')
    
    @api.onchange('employee_id')
    def onchange_employee(self):
        contract = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id)],order='id asc', limit=1)
        if self.employee_id and contract:
            self.employee_code = self.employee_id.code
            self.contract_id = contract[0] or False
            
class HrPayrollDeductionFixed(models.Model):
    _name = 'hr.payroll.deduction.fixed'
    _description = 'Fixed Deductible'
    
    deduction_id = fields.Many2one('hr.deduction', string='Deductible Name', required=True, ondelete='cascade')
    code = fields.Char('Deductible Code',size=240)
    name = fields.Char('Deductible Name')
    amount = fields.Float('Total')
    contract_id = fields.Many2one('hr.contract', string='Contract', ondelete='cascade')
    active = fields.Boolean('Active', default=True)
    employee_id = fields.Many2one('hr.employee', related='contract_id.employee_id', readonly=True, store=True)
    
    @api.onchange('deduction_id')
    def onchange_deduction_id(self):
        deduction = self.deduction_id
        self.code = deduction.code
        self.amount = deduction.amount
        
class HrPayrollDeductionMonthly(models.Model):
    _name = 'hr.payroll.deduction.monthly'
    _description = 'Monthly Deductible'

    deduction_id = fields.Many2one('hr.deduction', string='Deductible Name', required=True, ondelete='cascade')
    code = fields.Char('Code',size=240)
    amount = fields.Float('Amount')
    contract_id = fields.Many2one('hr.contract', string='Contract', ondelete='cascade')
    month = fields.Selection(SELECTION_MONTH, 
                              'Month', required=True, default=date.today().month)  
    year = fields.Integer('Year',required=True, default=date.today().year)
    active = fields.Boolean('Active', default=True)
    employee_id = fields.Many2one('hr.employee', related='contract_id.employee_id', readonly=True, store=True)
    
    @api.onchange('deduction_id')
    def onchange_deduction_id(self):
        deduction = self.deduction_id
        self.code = deduction.code
        self.amount = deduction.amount
        