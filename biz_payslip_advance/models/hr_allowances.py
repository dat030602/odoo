# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime, timedelta, date

SELECTION_MONTH = [('1','January'),('2','February'),('3','March'),('4','April'),
                              ('5','May'),('6','June'),('7','July'),('8','August'),
                              ('9','September'),('10','October'),('11','November'),('12','December')]

class HrAllowanceImport(models.Model):
    _name = 'hr.allowance.import'
    _description = 'Column Import Allowances'
    
    name = fields.Char('Name')
    allowance_id = fields.Many2one('hr.allowance', string='Allowance', default=False)
    
class hr_allowance(models.Model):
    _name = 'hr.allowance'
    _description = 'Allowances'
    
    name = fields.Char('Allowances')
    column_import = fields.Many2one('hr.allowance.import', string='Row number of import file')
    code = fields.Char('Allowances Code')
    amount = fields.Float('Total')
    is_fixed = fields.Boolean('Fixed')
    
    @api.model_create_multi
    def create(self, vals_list):
        allowance_objs = super(hr_allowance, self).create(vals_list)
        for allowance_obj in allowance_objs:
            if allowance_obj.column_import:
                allowance_obj.column_import.write({'allowance_id': allowance_obj.id})
        return allowance_objs
    
    def write(self,vals):
        for record in self:
            if 'column_import' in vals:
                column_import = vals.get('column_import',False)
                if record.column_import:
                    column_obj = self.env['hr.allowance.import'].browse(record.column_import.id)
                    column_obj.write({'allowance_id':False})
                if column_import:
                    column_obj = self.env['hr.allowance.import'].browse(column_import)
                    column_obj.write({'allowance_id': record.id})
        return super(hr_allowance, self).write(vals)
    
    
    def unlink(self):
        for record in self:
            if record.column_import:
                column_obj = self.env['hr.allowance.import'].browse(record.column_import.id)
                column_obj.write({'allowance_id':False})
        return super(hr_allowance, self).unlink()

class hr_payroll_allowance_import(models.Model):
    _name = 'hr.payroll.allowance.import'
    _description = 'Payroll Allowance Import'
    
    employee_code = fields.Char('Employee Code')
    employee_id = fields.Many2one('hr.employee', string='Employee Name')
    contract_id = fields.Many2one('hr.contract', string='Contract')
    update_id = fields.Many2one('hr.payroll.update', string='Payroll Update')
    allowances_1 = fields.Float('Allowances 1')
    allowances_2 = fields.Float('Allowances 2')
    allowances_3 = fields.Float('Allowances 3')
    allowances_4 = fields.Float('Allowances 4')
    allowances_5 = fields.Float('Allowances 5')
    allowances_6 = fields.Float('Allowances 6')
    allowances_7 = fields.Float('Allowances 7')
    allowances_8 = fields.Float('Allowances 8')
    allowances_9 = fields.Float('Allowances 9')
    allowances_10 = fields.Float('Allowances 10')
    allowances_11 = fields.Float('Allowances 11')
    allowances_12 = fields.Float('Allowances 12')
    allowances_13 = fields.Float('Allowances 13')
    allowances_14 = fields.Float('Allowances 14')
    allowances_15 = fields.Float('Allowances 15')
    allowances_16 = fields.Float('Allowances 16')
    allowances_17 = fields.Float('Allowances 17')
    allowances_18 = fields.Float('Allowances 18')
    allowances_19 = fields.Float('Allowances 19')
    allowances_20 = fields.Float('Allowances 20')
    allowances_21 = fields.Float('Allowances 21')
    allowances_22 = fields.Float('Allowances 22')
    allowances_23 = fields.Float('Allowances 23')
    allowances_24 = fields.Float('Allowances 24')
    allowances_25 = fields.Float('Allowances 25')
    allowances_26 = fields.Float('Allowances 26')
    allowances_27 = fields.Float('Allowances 27')
    allowances_28 = fields.Float('Allowances 28')
    allowances_29 = fields.Float('Allowances 29')
    allowances_30 = fields.Float('Allowances 30')
    allowances_31 = fields.Float('Allowances 31')
    allowances_32 = fields.Float('Allowances 32')
    allowances_33 = fields.Float('Allowances 33')
    allowances_34 = fields.Float('Allowances 34')
    allowances_35 = fields.Float('Allowances 35')

    
    @api.onchange('employee_id')
    def onchange_employee(self):
        contract = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id)], order='id asc', limit=1)
        if self.employee_id and contract:
            self.employee_code = self.employee_id.code
            self.contract_id = contract[0] or False
         
class HrPayrollAllowanceFixed(models.Model):
    _name = 'hr.payroll.allowance.fixed'
    _description = 'Fixed Allowances'
    
    allowance_id = fields.Many2one('hr.allowance', string='Allowances Name', required=True, ondelete='cascade')
    name = fields.Char('Allowances name')
    code = fields.Char('Allowances Code', size=240)
    amount = fields.Float('Total')
    contract_id = fields.Many2one('hr.contract', string='Contract', ondelete='cascade')
    active = fields.Boolean('Active', default=True)
    employee_id = fields.Many2one('hr.employee', related='contract_id.employee_id', readonly=True, store=True)
    
    @api.onchange('allowance_id')
    def onchange_allowance_id(self):
        allowance = self.allowance_id
        self.code = allowance.code
        self.amount = allowance.amount
    
    def unlink(self):
        for record in self:
            data_update = [{
                    'content_change':'earnings_kinds',
                    'hr_from': "%s-%s" % (record.allowance_id.name, record.amount) ,
                    'apply_date': datetime.now().date()
                }]
        return super(HrPayrollAllowanceFixed, self).unlink()

    # @api.model
    # def create(self,vals):
    #     data_update =[]
    #     res = super(HrPayrollAllowanceFixed, self).create(vals)
    #     if res.amount:
    #         data_update.append({
    #             'content_change':'earnings_kinds',
    #             'hr_to': "%s-%s" % (res.allowance_id.name, res.amount) ,
    #             'apply_date': datetime.now().date()

    #         })
    #     if data_update and res.contract_id and res.contract_id.employee_id:
    #         res.contract_id.employee_id.infor_change_person_ids = [(0,0, data) for data in data_update]
    #     return res

    # def write(self,vals):
    #     data_update = []
    #     if vals.get('amount',False):
    #         if vals.get('allowance_id',False):
    #             allowance_id = self.env['hr.allowance'].browse(vals.get('allowance_id',False))
    #         else:
    #             allowance_id = self.allowance_id
    #         data_update.append({
    #                 'content_change':'earnings_kinds',
    #                 'hr_from': "%s-%s" % (self.allowance_id.name, self.amount) ,
    #                 'hr_to': "%s-%s" % (allowance_id.name, vals.get('amount',False)) ,
    #                 'apply_date': datetime.now().date()
    #             })
    #     res = super(HrPayrollAllowanceFixed, self).write(vals)
    #     if data_update and self.employee_id:
    #         self.employee_id.infor_change_person_ids = [(0,0, data) for data in data_update]
    #     return res
        
class HrPayrollAllowanceMonthly(models.Model):
    _name = 'hr.payroll.allowance.monthly'
    _description = 'Monthly Allowances'

    allowance_id = fields.Many2one('hr.allowance','Allowances Name', required=True, ondelete='cascade')
    code = fields.Char('Code',size=240)
    amount = fields.Float('Amount')
    contract_id = fields.Many2one('hr.contract', string='Contract', ondelete='cascade')
    month = fields.Selection(SELECTION_MONTH, 
                              'Month', required=True, default=str(int(date.today().month))) 
    year = fields.Integer('Year',required=True, default=date.today().year)
    active = fields.Boolean('Active', default=True)
    employee_id = fields.Many2one('hr.employee', related='contract_id.employee_id', readonly=True, store=True)
    
    @api.onchange('allowance_id')
    def onchange_allowance_id(self):
        allowance = self.allowance_id
        self.code = allowance.code
        self.amount = allowance.amount
    