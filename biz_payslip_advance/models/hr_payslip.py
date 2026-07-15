# -*- coding: utf-8 -*-
from odoo import api, fields, models,tools, _
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import calendar
import time
from odoo.addons.hr_payroll.models.browsable_object import BrowsableObject, InputLine, WorkedDays, Payslips, ResultRules
DATE_FORMAT = "%Y-%m-%d"
import babel

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    is_probation = fields.Boolean('Probation',compute="_compute_is_probation",store=True,readonly=False)

    @api.depends('employee_id','date_from','date_to','contract_id.probation_date','contract_id.probation_end_date')
    def _compute_is_probation(self):
        for res in self:
            probation_date = res.contract_id.probation_date if res.contract_id and res.contract_id.probation_date else False
            probation_end_date = res.contract_id.probation_end_date if res.contract_id and res.contract_id.probation_end_date else False
            is_probation = False
            if probation_date and probation_end_date and res.date_to:
                is_probation = True if res.date_to >= probation_date and res.date_to <= probation_end_date else False
            res.is_probation = is_probation

    @api.model
    def get_input_workdays(self, contract, date_from, date_to):
        res = []
        for workday in contract.workday_ids:
            date_from_tmp = datetime.strptime(str(date_from), DATE_FORMAT)
            month_from = datetime.strftime(date_from_tmp, '%Y-%m')
            date_to_tmp = datetime.strptime(str(date_to), DATE_FORMAT)
            month_to = datetime.strftime(date_to_tmp, '%Y-%m')
            month = '%s-%s'%(str(workday.year).zfill(4), str(workday.month).zfill(2))
            if month < month_from or  month > month_to:
                continue
            workday_data = {
                    'name': workday.name,
                    'code': workday.code,
                    'number_of_days': workday.totay_days,
                    'number_of_hours': workday.totay_hours,
                    'contract_id': contract.id,
                }
            res .append((0, 0, workday_data))
        self.worked_days_line_ids = res
        return self.worked_days_line_ids

    @api.model
    def get_input_workdays_lines(self, contract, worked_days_line_ids, date_from, date_to):
        for workday in contract.workday_ids:
            date_from_tmp = datetime.strptime(str(date_from), DATE_FORMAT)
            month_from = datetime.strftime(date_from_tmp, '%Y-%m')
            date_to_tmp = datetime.strptime(str(date_to), DATE_FORMAT)
            month_to = datetime.strftime(date_to_tmp, '%Y-%m')
            month = '%s-%s'%(str(workday.year).zfill(4), str(workday.month).zfill(2))
            if month < month_from or  month > month_to:
                continue
            workday_data = {
                    'name': workday.name,
                    'code': workday.code,
                    'number_of_days': workday.totay_days,
                    'number_of_hours': workday.totay_hours,
                    'contract_id': contract.id,
                }
            if workday_data not in worked_days_line_ids:
                worked_days_line_ids.append(workday_data)
        return worked_days_line_ids

    def _get_new_worked_days_lines(self):
        # hr.payslip.worked_days
        HP_worked_days = super(HrPayslip, self)._get_new_worked_days_lines()
        if isinstance(HP_worked_days, list):
            HP_worked_days = self.worked_days_line_ids.browse([])
            
        if self.contract_id:
            # hr.contract.workday
            HC_worked_days = self.contract_id.mapped('workday_ids').\
                                    filtered(lambda l: l.date_time.date()>= self.date_from and l.date_time.date()<self.date_to)
            
            HP_worked_days = self._generate_worked_day_lines_by(HC_worked_days, HP_worked_days)
         
        return  HP_worked_days
    

    def _generate_worked_day_lines_by(self, HC_worked_days, HP_worked_days):
        for line in HC_worked_days:
            work_entry_type_id = self.env['hr.work.entry.type'].search([('code','=', line.code)], limit=1)
            worked_days_lines = self.worked_days_line_ids.browse([])
            
            if work_entry_type_id and work_entry_type_id not in HP_worked_days.mapped('work_entry_type_id'):
                item = {
                    'payslip_id': self.id,
                    'sequence': work_entry_type_id.sequence,
                    'work_entry_type_id': work_entry_type_id.id,
                    'number_of_days': line.totay_days,
                    'number_of_hours': line.totay_hours
                }
                HP_worked_days |= worked_days_lines.new(item)
            elif work_entry_type_id and  work_entry_type_id in HP_worked_days.mapped('work_entry_type_id'):
                worked_days_line = HP_worked_days.filtered(lambda l: l.work_entry_type_id == work_entry_type_id)
                worked_days_line.number_of_days += line.totay_days
                worked_days_line.number_of_hours += line.number_of_hours

        return HP_worked_days

    def get_input_type(self, code, name=False):
        if not code:
            return False

        type_id = self.env['hr.payslip.input.type'].search([('code','=', code),('struct_ids','in', self.struct_id.ids)], limit=1)
        if not type_id:
            type_id = self.env['hr.payslip.input.type'].create({
                'name': name or code,
                'code': code,
                'struct_ids': [(6,0, self.struct_id.ids)]
            })
        return type_id or False
        
    @api.model
    def get_inputs(self, contracts, date_from, date_to):
        res = super(HrPayslip, self).get_inputs(contracts, date_from, date_to)
        day_from = fields.Datetime.from_string(date_from)
        day_to = fields.Datetime.from_string(date_to)
        day_f= day_from.date()
        day_t= day_to.date()
        for contract in contracts:
            for allowance in contract.allowance_month_ids:
                year = int(allowance.year)
                month = int(allowance.month)
                month_range = calendar.monthrange(year, month)       
                date_end = datetime(year, month, month_range[1]).date()
                date_start = datetime(year, month, 1).date()
                if (date_end >= day_f and date_end <= day_t) or (date_start >= day_f and date_start<= day_t) or (date_end >=day_f and date_start <=day_t):
                    type_id = self.get_input_type(allowance.code, allowance.allowance_id.name)
                    if type_id:
                        allowance_data = {
                            'name': allowance.allowance_id.name,
                            'code': allowance.code,
                            'amount': allowance.amount,
                            'contract_id': contract.id,
                            'input_type_id': type_id.id,
                        }
                        res += [allowance_data]
             
            for deduction in contract.deduction_month_ids:
                year = int(deduction.year)
                month = int(deduction.month)
                month_range = calendar.monthrange(year, month)       
                date_end = datetime(year, month, month_range[1]).date()
                date_start = datetime(year, month, 1).date()
                if (date_end >= day_f and date_end <= day_t) or (date_start >= day_f and date_start<= day_t) or (date_end >=day_f and date_start <=day_t):
                    type_id = self.get_input_type(deduction.code, deduction.deduction_id.name)
                    if type_id:
                        deduction_data = {
                            'name': deduction.deduction_id.name,
                            'code': deduction.code,
                            'amount': deduction.amount,
                            'input_type_id': type_id.id,
                            'contract_id': contract.id,
                        }
                        res += [deduction_data]
             
            for allowance in contract.allowance_fix_ids:
                type_id = self.get_input_type(allowance.code, allowance.allowance_id.name)
                if type_id:
                    allowance_fix = {
                            'name': allowance.allowance_id.name,
                            'code': allowance.code,
                            'amount': allowance.amount,
                            'input_type_id': type_id.id,
                            'contract_id': contract.id,
                        }
                    res += [allowance_fix]
                 
            for deduction in contract.deduction_fix_ids:
                type_id = self.get_input_type(deduction.code, deduction.deduction_id.name)
                if type_id:
                    deduction_fix = {
                            'name': deduction.deduction_id.name,
                            'code': deduction.code,
                            'amount': deduction.amount,
                            'input_type_id': type_id.id,
                            'contract_id': contract.id,
                        }
                    res += [deduction_fix]

            for workday in contract.workday_ids:
                date_from_tmp = datetime.strptime(str(date_from), DATE_FORMAT)
                month_from = datetime.strftime(date_from_tmp, '%Y-%m')
                date_to_tmp = datetime.strptime(str(date_to), DATE_FORMAT)
                month_to = datetime.strftime(date_to_tmp, '%Y-%m')
                month = '%s-%s'%(str(workday.year).zfill(4), str(workday.month).zfill(2))
                if month < month_from or  month > month_to:
                    continue
                type_id = self.get_input_type(workday.code, workday.name)
                
                if type_id:
                    amount = 0
                    if workday.totay_days:
                        amount = workday.totay_days
                    if workday.totay_hours:
                        amount = workday.totay_hours
                    workday_fix = {
                            'name': workday.name,
                            'code': workday.code,
                            'amount': amount,
                            'input_type_id': type_id.id,
                            'contract_id': contract.id,
                        }
                    res += [workday_fix]

            search_config = self.env['config.salary.insurence.union.dues'].search([('date_apply','<=',date_from)],order="id asc")
            list_config = {}
            for se in search_config:
                list_index = se.rule_apply
                if list_index not in list_config:
                    list_config[list_index] = {
                        'name': list_index.name,
                        'code': list_index.code,
                        'amount': se.maximum_amount,
                        'input_type_id': list_index.id,
                        'contract_id': contract.id,
                        'is_config_salary': True
                    }
                    res += [list_config[list_index]]
                 
        return res

    def get_mail_month(self):
        if self.date_from:
            month = self.date_from.month
            year = self.date_from.year
            month_b = self.date_from.strftime("%B")
            return 'Tháng %s.%s/Month: %s %s' % (month,  year, month_b, year)
        return ''

    def action_sent_payslip_detail(self):
        template = self.env.ref('biz_payslip_advance.template_send_mail_payslip_ccv')
        for res in self:
            if template and res.employee_id:
                template.send_mail(res.id, force_send=True)

class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    is_config_salary = fields.Boolean()