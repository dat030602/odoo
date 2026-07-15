# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
import os
import xlrd
import base64
import calendar
SELECTION_MONTH = [('1','January'),('2','February'),('3','March'),('4','April'),
                              ('5','May'),('6','June'),('7','July'),('8','August'),
                              ('9','September'),('10','October'),('11','November'),('12','December')]

def RepresentsFloat(s):
    try: 
        float(s)
        return True
    except ValueError:
        return False

class hr_payroll_update(models.Model):
    _name = 'hr.payroll.update'
    _description = 'Payroll Update'
    
    name = fields.Char('Name', default='Update to salary in month ' + str(date.today().month) + '/' + str(date.today().year))
    month = fields.Selection(SELECTION_MONTH, string='Month', required=True, default=str(date.today().month))
    year = fields.Char('Year', required=True, default=str(date.today().year))
    show_workday = fields.Boolean('Show Workday')
    file_import = fields.Binary(string='Chọn file')
    file_name = fields.Char('File Name', size=64)
    allowance_ids = fields.One2many('hr.payroll.allowance.import', 'update_id', string='Allowances')
    deduction_ids = fields.One2many('hr.payroll.deduction.import', 'update_id', string='Deductions')
    working_day_ids = fields.One2many('hr.working.day.import', 'update_id', string='Working Day')
    state = fields.Selection([('draft', 'Draft'),('confirmed','Update Expenses'),('done', 'Done')], string='Status', readonly=True, default='draft')
    
    @api.onchange('month', 'year')
    def onchange_name(self):
        if not self.month or not self.year:
            return {}
        self.name = 'Update to salary in month %s/%s'%(self.month, self.year)
        
    def save_file(self, name, value):
        type_path = '/tmp/biz_payslip_advance'
        if not os.path.exists(type_path):
            os.mkdir(type_path)
        path = '%s/%s' % (type_path,name)       
        f = open( path, 'wb+' )
        try:
            f.write( base64.b64decode( value ) )
        finally:
            f.close()
        return path
    
    def get_employee_code(self, employee_name):
        employee_pool = self.env['hr.employee'].with_context(active_test=False)
        if not employee_name:
            return False
        clean_name = employee_name.strip()
        
        # 1. Try exact match first (standard Odoo logic)
        employee_ids = employee_pool.search(['|', ('code', '=', clean_name), ('name', '=', clean_name)])
        if employee_ids:
            return employee_ids[0]
            
        # 2. Try matching without department prefixes & double spaces
        name_without_prefix = clean_name
        for prefix in ["KD.ASM", "KD.SA", "KD.SM", "KD.SR", "KD.SS", "KD.TS", "KD.SD"]:
            if name_without_prefix.upper().startswith(prefix):
                name_without_prefix = name_without_prefix[len(prefix):].strip()
                if name_without_prefix.startswith("-"):
                    name_without_prefix = name_without_prefix[1:].strip()
                    
        name_without_prefix = " ".join(name_without_prefix.split())
        
        # Search by code or by name (case-insensitive substring)
        employee_ids = employee_pool.search(['|', ('code', '=', clean_name), ('name', 'ilike', name_without_prefix)])
        if employee_ids:
            return employee_ids[0]
            
        return False
    
    def check_validate_float_value(self, row, line_current, sheet_name):
        try:
            if row[2] and not RepresentsFloat(row[2]):
                raise UserError(_(u'Dữ liệu ở ô C%s Sheet %s phải là số!'% (str(line_current), sheet_name)))
            if row[3] and not RepresentsFloat(row[3]):
                raise UserError(_(u'Dữ liệu ở ô D%s Sheet %s phải là số!'% (str(line_current), sheet_name)))
            if row[4] and not RepresentsFloat(row[4]):
                raise UserError(_(u'Dữ liệu ở ô E%s Sheet %s phải là số!'% (str(line_current), sheet_name)))
            if row[5] and not RepresentsFloat(row[5]):
                raise UserError(_(u'Dữ liệu ở ô F%s Sheet %s phải là số!'% (str(line_current), sheet_name)))
            if row[6] and not RepresentsFloat(row[6]):
                raise UserError(_(u'Dữ liệu ở ô G%s Sheet %s phải là số!'% (str(line_current), sheet_name)))
            if row[7] and not RepresentsFloat(row[7]):
                raise UserError(_(u'Dữ liệu ở ô H%s Sheet %s phải là số!'% (str(line_current), sheet_name)))
            if row[8] and not RepresentsFloat(row[8]):
                raise UserError(_(u'Dữ liệu ở ô I%s Sheet %s phải là số!'% (str(line_current), sheet_name)))
            if row[9] and not RepresentsFloat(row[9]):
                raise UserError(_(u'Dữ liệu ở ô J%s Sheet %s phải là số!'% (str(line_current), sheet_name)))
            if row[10] and not RepresentsFloat(row[10]):
                raise UserError(_(u'Dữ liệu ở ô K%s Sheet %s phải là số!'% (str(line_current), sheet_name)))
            if row[11] and not RepresentsFloat(row[11]):
                raise UserError(_(u'Dữ liệu ở ô L%s Sheet %s phải là số!'% (str(line_current), sheet_name)))
        except:
            raise UserError(_(u'Mising columns, Please check template again....'))
        return True
    
    @api.model
    def check_employee(self, employee_name, employee_code, line_current, sheet):
        if not employee_name:
            raise UserError(_(u'Vui lòng điền tên nhân viên cho %s - %s cột A'% (str(line_current), sheet.name)))
        employee_id = self.get_employee_code(u'%s' % employee_name)
        employee_id_2 = self.get_employee_code(u'%s' % employee_code)
        if employee_name and not (employee_id and employee_id_2 and employee_id == employee_id_2):
            raise UserError(_(u'Không tìm thấy nhân viên tương ứng. Vui lòng kiểm tra lại dữ liệu Mã nhân viên hoặc Tên nhân viên của dòng %s - %s'% (str(line_current), sheet.name)))
        return employee_id
    
    
    def action_load(self):
        context = dict(self._context or {})
        path = '/tmp/biz_payslip_advance/'
        working_day = self.env['hr.working.day.import']
        payroll_phucap_import = self.env['hr.payroll.allowance.import']
        allowance_env = self.env['hr.allowance']
        reduces_import = self.env['hr.payroll.deduction.import']
        reduces_pool = self.env['hr.deduction']
        hr_contract = self.env['hr.contract']
        type_workday = self.env['hr.type.working.day']
        allowance_monthly = self.env['hr.payroll.allowance.monthly']
        deduction_monthly = self.env['hr.payroll.deduction.monthly']
        hr_working_day_pool = self.env['hr.contract.workday']
        for data in self:
            data.allowance_ids.unlink()
            data.deduction_ids.unlink()
            data.working_day_ids.unlink()
            
            if not data.file_name or not data.file_import:
                raise UserError(_('You have must chosen a file!'))
            path = self.save_file(data.file_name, data.file_import)          
            try:
                book = xlrd.open_workbook(path)
            except:                
                raise UserError(_('Not found file!. Please check path....'))
            if book.nsheets < 3 :
                raise UserError(_('Please check file again!'))
            year = int(data.year)
            month = int(data.month)
            month_range = calendar.monthrange(year, month)
            date_start = datetime(year, month, 1).date()
            date_end = datetime(year, month, month_range[1]).date()
            
            #WORKDAY
            if data.show_workday:
                sheet_workday = book.sheet_by_index(2)
                if sheet_workday._cell_values:
                    name_field_workday = sheet_workday._cell_values[2][0:sheet_workday.ncols]
                    header_workday = []
                    code_workday = 1
                    for workday in name_field_workday[2:]:
                        workday_type_ids = type_workday.search([('column_import.name','=',code_workday)])
                        type_id = workday_type_ids and workday_type_ids[0] or False
                        header_workday.append(type_id)
                        code_workday += 1
                    line_current = 3
                    
                    for row in sheet_workday._cell_values[3:]:
                        line_current += 1
                        employee_code = row[0]
                        try:
                            if employee_code % 1 == 0:
                                employee_code = int(employee_code)
                        except:
                            pass
                        employee_name = row[1]
                        #Kiểm tra nhân viên có tồn tại trong hệ thống
                        employee_id = self.check_employee(employee_name, employee_code, line_current, sheet_workday)
                        self.check_validate_float_value(row, line_current, sheet_workday.name)
                        contract_obj = hr_contract.search([('employee_id','=',employee_id.id),('state','=','open'),'|',('date_start','<=',date_start),('date_start','<=',date_end),'|','|',('date_end','>=',date_end),('date_end','>=',date_start),('date_end','=',False)], order="id asc", limit=1)
                        if contract_obj:
                            index_current = 0;
                            for cell_value in row[2:]:
                                if cell_value and header_workday[index_current]:
                                    type_working_id = header_workday[index_current]
                                    working_obj = hr_working_day_pool.search([('code','=',type_working_id.code),('name','=',type_working_id.name),('year','=',year),('month','=',int(month)),('contract_id','=',contract_obj.id)])
                                    if working_obj:
                                        vals= {
                                               'totay_days': 0,
                                               'totay_hours':0,
                                               }
                                        if not type_working_id.type_value:
                                            raise UserError(_(u'Vui lòng cấu hình loại giá trị trong Cấu hình ngày công Import của %s' % type_working_id.name))
                                        elif type_working_id.type_value == 'day':
                                            vals['totay_days'] = float(cell_value)
                                        elif type_working_id.type_value == 'hours':
                                            vals['totay_hours'] = float(cell_value)   
                                        for work in working_obj:
                                            work.write(vals)       
                                    else:
                                        vals_working_day = {
                                                    'name': type_working_id.name,
                                                    'code': type_working_id.code,                                            
                                                    'contract_id': contract_obj.id,
                                                    'employee_id': employee_id.id,
                                                    'date_time': datetime(year=year, month=month, day=1),
                                                    'month': str(month),
                                                    'year': year,
                                                    }
                                        if not type_working_id.type_value:
                                            raise UserError(_(u'Vui lòng cấu hình loại giá trị trong Cấu hình ngày công Import của %s' % type_working_id.name))
                                        elif type_working_id.type_value == 'day':
                                            vals_working_day['totay_days'] = float(cell_value)
                                        elif type_working_id.type_value == 'hours':
                                            vals_working_day['totay_hours'] = float(cell_value)
                                        hr_working_day_pool.create(vals_working_day)
                                index_current += 1       
                        working_day.create({
                                            'employee_code': employee_id.code,
                                            'employee_id': employee_id.id,
                                            'day_type_1': header_workday[0] and row[2] and float(row[2]) or 0.0,
                                            'day_type_2': header_workday[1] and row[3] and float(row[3]) or 0.0,
                                            'day_type_3': header_workday[2] and row[4] and float(row[4]) or 0.0,
                                            'day_type_4': header_workday[3] and row[5] and float(row[5]) or 0.0,
                                            'day_type_5': header_workday[4] and row[6] and float(row[6]) or 0.0,
                                            'day_type_6': header_workday[5] and row[7] and float(row[7]) or 0.0,
                                            'day_type_7': header_workday[6] and row[8] and float(row[8]) or 0.0,
                                            'day_type_8': header_workday[7] and row[9] and float(row[9]) or 0.0,
                                            'day_type_9': header_workday[8] and row[10] and float(row[10]) or 0.0,
                                            'day_type_10': header_workday[9] and row[11] and float(row[11]) or 0.0,
                                            'update_id': data.id,
                                            'contract_id': contract_obj.id if contract_obj else False,
                                        })
            #ALLOWANCE    
            sheet_allowance = book.sheet_by_index(0)
            if sheet_allowance._cell_values:
                name_field_allowance = sheet_allowance._cell_values[2][0:sheet_allowance.ncols]
                header_allowance = []
                code_allowance = 1
                context_temp = context.copy()
                context_temp.update({'active_test':False})
                for allowance in name_field_allowance[2:]:
                    allowance_code_temp = 'ALLOWANCE%s' % code_allowance
                    allowance_ids = allowance_env.search([('column_import','=',allowance_code_temp)])
                    if not allowance_ids:
                        type_id = False
                    else:
                        type_id = allowance_ids and allowance_ids[0]
                    header_allowance.append(type_id)
                    code_allowance += 1
                line_current = 3

                    
                for row in sheet_allowance._cell_values[3:]:
                    line_current += 1
                    employee_code = row[0]
                    try:
                        if employee_code % 1 == 0:
                            employee_code = int(employee_code)
                    except:
                        pass
                    employee_name = row[1]
                    #Kiểm tra nhân viên có tồn tại trong hệ thống
                    employee_id = self.check_employee(employee_name, employee_code, line_current, sheet_allowance)
                    self.check_validate_float_value(row, line_current, sheet_allowance.name)
                    contract_obj = hr_contract.search([('employee_id','=',employee_id.id),('state','=','open'),'|',('date_start','<=',date_start),('date_start','<=',date_end),'|','|',('date_end','>=',date_end),('date_end','>=',date_start),('date_end','=',False)], order="id asc", limit=1)
                    if contract_obj:
                        index_current = 0;
                        for cell_value in row[2:]:
                            if cell_value and header_allowance[index_current]:
                                allowance_id = header_allowance[index_current]
                                allowance_obj = allowance_monthly.search([('year','=',year),('month','=',int(month)),('contract_id','=',contract_obj.id),('allowance_id','=',allowance_id.name),('code','=',allowance_id.code)])
                                if allowance_obj:
                                    for allowance in allowance_obj:
                                        allowance.write({'amount':float(cell_value)})
                                else:
                                    allowance_monthly.create({
                                                'month': str(month),
                                                'year': year,
                                                'allowance_id': allowance_id.id,
                                                'code': allowance_id.code,
                                                'amount': float(cell_value),
                                                'contract_id': contract_obj.id})
                            index_current += 1

                    demo_data = {
                                'employee_code': employee_id.code,
                                'employee_id': employee_id.id,
                                'allowances_1': self.get_row_index(header_allowance, row, 0, 2),
                                'allowances_2': self.get_row_index(header_allowance, row, 1, 3),
                                'allowances_3': self.get_row_index(header_allowance, row, 2, 4),
                                'allowances_4': self.get_row_index(header_allowance, row, 3, 5),
                                'allowances_5': self.get_row_index(header_allowance, row, 4, 6),
                                'allowances_6': self.get_row_index(header_allowance, row, 5, 7),
                                'allowances_7': self.get_row_index(header_allowance, row, 6, 8),
                                'allowances_8': self.get_row_index(header_allowance, row, 7, 9),
                                'allowances_9': self.get_row_index(header_allowance, row, 8, 10),
                                'allowances_10': self.get_row_index(header_allowance, row, 9, 11),
                                'allowances_11': self.get_row_index(header_allowance, row, 10, 12),
                                'allowances_12': self.get_row_index(header_allowance, row, 11, 13),
                                'allowances_13': self.get_row_index(header_allowance, row, 12, 14),
                                'allowances_14': self.get_row_index(header_allowance, row, 13, 15),
                                'allowances_15': self.get_row_index(header_allowance, row, 14, 16),
                                'allowances_16': self.get_row_index(header_allowance, row, 15, 17),
                                'allowances_17': self.get_row_index(header_allowance, row, 16, 18),
                                'allowances_18': self.get_row_index(header_allowance, row, 17, 19),
                                'allowances_19': self.get_row_index(header_allowance, row, 18, 20),
                                'allowances_20': self.get_row_index(header_allowance, row, 19, 21),
                                'allowances_21': self.get_row_index(header_allowance, row, 20, 22),
                                'allowances_22': self.get_row_index(header_allowance, row, 21, 23),
                                'allowances_23': self.get_row_index(header_allowance, row, 22, 24),
                                'allowances_24': self.get_row_index(header_allowance, row, 23, 25),
                                'allowances_25': self.get_row_index(header_allowance, row, 24, 26),
                                'allowances_26': self.get_row_index(header_allowance, row, 25, 27),
                                'allowances_27': self.get_row_index(header_allowance, row, 26, 28),
                                'allowances_28': self.get_row_index(header_allowance, row, 27, 29),
                                'allowances_29': self.get_row_index(header_allowance, row, 28, 30),
                                'allowances_30': self.get_row_index(header_allowance, row, 29, 31),
                                'allowances_31': self.get_row_index(header_allowance, row, 30, 32),
                                'allowances_32': self.get_row_index(header_allowance, row, 31, 33),
                                'allowances_33': self.get_row_index(header_allowance, row, 32, 34),
                                'allowances_34': self.get_row_index(header_allowance, row, 33, 35),
                                'allowances_35': self.get_row_index(header_allowance, row, 34, 36),
                                'update_id': data.id,
                                'contract_id': contract_obj.id if contract_obj else False,
                            }
                    payroll_phucap_import.create(demo_data)
            #DEDUCTION
            sheet_deduction = book.sheet_by_index(1)
            if sheet_deduction._cell_values:
                name_field_deduction = sheet_deduction._cell_values[2][0:sheet_deduction.ncols]
                header_deduction = []
                code_deduction = 1
                for deduction in name_field_deduction[2:]:
                    deduction_code_temp = 'DEDUCTION%s' % code_deduction
                    deduction_ids = reduces_pool.search([('column_import','=',deduction_code_temp)])                
                    if not deduction_ids:
                        type_id = False
                    else:
                        type_id = deduction_ids and deduction_ids[0]
                    header_deduction.append(type_id)
                    code_deduction += 1
                line_current = 3
                for row in sheet_deduction._cell_values[3:]:
                    line_current += 1
                    employee_code = row[0]
                    try:
                        if employee_code % 1 == 0:
                            employee_code = int(employee_code)
                    except:
                        pass
                    employee_name = row[1]
                    #Kiểm tra nhân viên có tồn tại trong hệ thống
                    employee_id = self.check_employee(employee_name, employee_code, line_current, sheet_deduction)
                    self.check_validate_float_value(row, line_current, sheet_deduction.name)
                    contract_obj = hr_contract.search([('employee_id','=',employee_id.id),('state','=','open'),'|',('date_start','<=',date_start),('date_start','<=',date_end),'|','|',('date_end','>=',date_end),('date_end','>=',date_start),('date_end','=',False)], order="id asc", limit=1)
                    if contract_obj:
                        index_current = 0
                        for cell_value in row[2:]:
                            if cell_value and header_deduction[index_current]:
                                deduction_id = header_deduction[index_current]
                                deduction_obj = deduction_monthly.search([('code','=',deduction_id.code),('deduction_id','=',deduction_id.name),('year','=',year),('month','=',int(month)),('contract_id','=',contract_obj.id)])
                                if deduction_obj:
                                    for deduc in deduction_obj:
                                        deduc.write({'amount':float(cell_value)}) 
                                else:
                                    vals = {
                                        'deduction_id':deduction_id.id,
                                        'code':deduction_id.code,
                                        'amount': float(cell_value), 
                                        'contract_id': contract_obj.id,
                                        'month': str(month),
                                        'year': year,
                                        }
                                    deduction_monthly.create(vals)
                            index_current += 1                                                
                    reduces_import.create({
                                        'employee_code': employee_id.code,
                                        'employee_id': employee_id.id,
                                        'deduction_1': header_deduction[0] and row[2] and float(row[2]) or 0.0,
                                        'deduction_2': header_deduction[1] and row[3] and float(row[3]) or 0.0,
                                        'deduction_3': header_deduction[2] and row[4] and float(row[4]) or 0.0,
                                        'deduction_4': header_deduction[3] and row[5] and float(row[5]) or 0.0,
                                        'deduction_5': header_deduction[4] and row[6] and float(row[6]) or 0.0,
                                        'deduction_6': header_deduction[5] and row[7] and float(row[7]) or 0.0,
                                        'deduction_7': header_deduction[6] and row[8] and float(row[8]) or 0.0,
                                        'deduction_8': header_deduction[7] and row[9] and float(row[9]) or 0.0,
                                        'deduction_9': header_deduction[8] and row[10] and float(row[10]) or 0.0,
                                        'deduction_10': header_deduction[9] and row[11] and float(row[11]) or 0.0,
                                        'update_id': data.id,
                                        'contract_id': contract_obj.id if contract_obj else False,
                                    })
            
        return self.write({'state':'done'})

    def get_row_index(self, header, row, header_index, row_index):
        if len(header) - 1 >= header_index and len(row) - 1 >= row_index:
            return row[row_index]
        return 0
    
    
class hr_working_day_import(models.Model):
    _name = 'hr.working.day.import'
    _description = 'Working Day Import'
    
    contract_id = fields.Many2one('hr.contract', string='Contract')
    update_id = fields.Many2one('hr.payroll.update', string='Payroll Update')
    employee_code = fields.Char('Employee Code')
    employee_id = fields.Many2one('hr.employee', string='Employee Name')
    day_type_1 = fields.Float('Day Type 1')
    day_type_2 = fields.Float('Day Type 2')
    day_type_3 = fields.Float('Day Type 3')
    day_type_4 = fields.Float('Day Type 4')
    day_type_5 = fields.Float('Day Type 5')
    day_type_6 = fields.Float('Day Type 6')
    day_type_7 = fields.Float('Day Type 7')
    day_type_8 = fields.Float('Day Type 8')
    day_type_9 = fields.Float('Day Type 9')
    day_type_10 = fields.Float('Day Type 10')
                
                