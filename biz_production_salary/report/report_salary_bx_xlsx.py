# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime,date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import base64
import io
from urllib.request import Request, urlopen
import calendar
from dateutil.relativedelta import relativedelta
from odoo.osv import expression


class report_salary_bx_xlsx(models.AbstractModel):
    _name = 'report.biz_production_salary.report_salary_bx_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'report_salary_bx_xlsx'
    
    def generate_xlsx_report(self, workbook, data, o):
        self = self.with_context(lang=self.env.user.lang)
        table_border_head = {
            'font_name': 'Times New Roman', 'font_size': 12, 'text_wrap': True, 
            'align': 'center','border':True,'bold':True
        }
        table_border_body = {'font_name': 'Times New Roman', 'font_size': 12, 'align': 'left','border':True}

        def get_format(*arguments):
            normal_style = {'font_name': 'Times New Roman', 'font_size': 12,'valign':'vcenter','align': 'left'}
            for arg in arguments:
                normal_style.update(arg)
            return workbook.add_format(normal_style)

        date_print = 'THÁNG %s NĂM %s'%(o.month,o.year)
        for department in o.department_ids:
            department_name = department.name.upper()
            sheet = workbook.add_worksheet(department_name)
            sheet.set_margins(0.25,0.25,0.25,0.75)
            #set column cho stt và họ và tên
            sheet.set_column(0,0,5)
            sheet.set_column(1,1,45)
            
            largest,cols,title_header,lines = self.get_data_excel(o,department)
            #set column cho các tháng
            for i in range(len(title_header)):
                if i not in [0,1] and i < largest + 2:
                    sheet.set_column(i,i,10)
                if i >= largest + 2:
                    sheet.set_column(i,i,20)

            y_offset = 0
            sheet.merge_range(y_offset, 0, y_offset, len(title_header), 'BẢNG LƯƠNG %s %s'%(department_name,date_print), 
                get_format({'align': 'center','font_size': 18, 'bold': True}))
            y_offset += 1
            sheet.set_row(y_offset, 25)
            i = 0
            for title in title_header:
                sheet.write(y_offset, i, title, get_format(table_border_head))
                i += 1
            y_offset += 1
            for line in lines:
                bold_total = False
                if line.get('line_total'):
                    bold_total = True
                for key,val in line.items():
                    if key == 'line_total':
                        continue
                    add_style = {}
                    if key not in ['stt','name']:
                        add_style.update({'align':'right', 'num_format': '#,##0'})
                        if not val:
                            val = 0
                    if bold_total:
                        if key == 'stt':
                            val = ''
                        if key == 'name':
                            add_style.update({'bold': True})
                    sheet.write(y_offset, cols[key], val, get_format(table_border_body,add_style))
                y_offset += 1

            y_offset += 3
            sheet.merge_range(y_offset, 0, y_offset, 1, 'NGƯỜI LẬP', get_format({'align': 'center','font_size': 14, 'bold': True}))
            sheet.merge_range(y_offset, 4, y_offset, 6, 'PHÒNG HCNS', get_format({'align': 'center','font_size': 14, 'bold': True}))
            sheet.merge_range(y_offset, 8, y_offset, 10, 'P.TCKT', get_format({'align': 'center','font_size': 14, 'bold': True}))
            sheet.merge_range(y_offset, 12, y_offset, 14, 'TỔNG GIÁM ĐỐC', get_format({'align': 'center','font_size': 14, 'bold': True}))
            y_offset += 5
            sheet.merge_range(y_offset, 0, y_offset, 1, o.founder_id.name or '', get_format({'align': 'center','font_size': 14, 'bold': True}))
            sheet.merge_range(y_offset, 4, y_offset, 6, o.hcns_department_id.name or '', get_format({'align': 'center','font_size': 14, 'bold': True}))
            sheet.merge_range(y_offset, 8, y_offset, 10, o.tckt_department_id.name or '', get_format({'align': 'center','font_size': 14, 'bold': True}))
            sheet.merge_range(y_offset, 12, y_offset, 14, o.unit_head_id.name or '', get_format({'align': 'center','font_size': 14, 'bold': True}))

    def get_data_excel(self,o,department):
        cols = {
            'stt': 0,
            'name': 1,
        }
        title_header = ['Stt','Họ và tên']
        PaySlip = self.env['hr.payslip'].sudo()
        TotalAmountReceivedByday = self.env['total.amount.received.byday'].sudo()
        res = []
        year = int(o.year)
        month = int(o.month)
        #tìm xem có bao nhiêu ngày trong tháng thì thêm bấy nhiêu cột
        get_all_days = calendar.monthcalendar(int(o.year), int(o.month))
        largest = False
        for days in get_all_days:
            largest = max(days)
        #update cột cols + title_header 
        y = 2
        for i in range(largest):
            cols.update({i+1: y})
            title_header.append(str(i+1))
            y += 1
        #tổng hợp dòng in excel
        date_from = date(year, month, 1)
        date_to = date_from + relativedelta(months=1) - relativedelta(days=1)
        domain = [('state','not in',['draft','cancel']),('employee_id.department_id','=',department.id)]
        domain_date = expression.OR([[('date_from', '>=', date_from), ('date_from', '<=', date_to)], [('date_to', '>=', date_from), ('date_to', '<=', date_to)]])
        domain = expression.AND([domain, domain_date])
        payslips = PaySlip.search(domain)
        data_add = {}
        for name in payslips.mapped('line_ids').mapped('name'):
            data_add.update({name: False})
            if not cols.get(name):
                cols.update({name: y})
                title_header.append(name)
                y += 1
        stt = 0
        total_data = {'stt': False, 'name': 'TỔNG CỘNG','line_total':True}
        for pay in payslips:
            data = {'stt': stt,'name': pay.employee_id.name}
            data.update(data_add)
            stt += 1
            for i in range(largest):
                total = TotalAmountReceivedByday.search([('production_date','=',date(year, month, i+1)),('employee_id','=',pay.employee_id.id),('summary_id.department_id','=',department.id)],limit=1)
                data.update({i+1: total.amount_received if total else 0})
                if not total_data.get(i+1):
                    total_data.update({i+1: total.amount_received})
                else:
                    total_data[i+1] += total.amount_received
            for line in pay.line_ids:
                data.update({line.name: line.total})
                if not total_data.get(line.name):
                    total_data.update({line.name: line.total})
                else:
                    total_data[line.name] += line.total
            res.append(data)
        # for k,v in total_data.items():
            # if k not in ['stt','name','line_total']:
                # total_data.update({k: '{:,.0f}'.format(v).replace(',','.')})
        res.append(total_data)
        return largest,cols,title_header,res
