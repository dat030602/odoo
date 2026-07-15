# -*- coding: utf-8 -*-
from odoo import models, _
from datetime import datetime

class ReportSalarySlipExcel(models.AbstractModel):
    _name = 'report.biz_payslip_excel_report.report_salary_slip_excel'
    _description = 'Report Salary Slip Excel'
    _inherit = 'report.report_xlsx.abstract'
    
    def generate_xlsx_report(self, workbook, data, details):
        self = self.with_context(lang=self.env.user.lang)
        for o in details:
            company_id = self.env.company
            def get_format(*arguments):
                normal_style = {'font_name': 'Times New Roman', 'font_size': 12, 'valign': 'vcenter', 'align': 'left'}
                for arg in arguments:
                    normal_style.update(arg)
                return workbook.add_format(normal_style)
            company = {'bold': True, 'font_size': 13, 'text_wrap': True, 'align': 'left'}
            report_title = {'bold': True, 'font_size': 14, 'text_wrap': True, 'align': 'center'}
            
            worksheet_name = (_("Phiếu lương %s" % o.employee_id.name if o.employee_id else ''))
            sheet = workbook.add_worksheet(worksheet_name)
            
            sheet.set_column(0,1,20)
            sheet.set_column(1,2,20)
            sheet.set_column(2,2,20)
            
            y_offset = 0
            sheet.merge_range(y_offset, 0, y_offset, 2, company_id.name.upper(), get_format(company))
            y_offset +=1
            sheet.merge_range(y_offset, 0, y_offset, 2, "PHIẾU NHẬN LƯƠNG", get_format(report_title))
            y_offset +=1
            sheet.merge_range(y_offset, 0, y_offset, 2, o.payslip_run_id.name if o.payslip_run_id else '', get_format(report_title))
            y_offset +=1
            sheet.merge_range(y_offset, 0, y_offset, 1, 'Họ và tên nhân viên', get_format())
            sheet.write(y_offset, 2, o.employee_id.name if o.employee_id else '' , get_format())
            y_offset +=1
            
            if 'Kinh Doanh' in o.struct_id.name or 'KDVP' in o.struct_id.name:
                report_lines = o.get_kd_custom_report_lines()
                for line in report_lines:
                    is_bold = line.get('is_bold', False)
                    sheet.merge_range(y_offset, 0, y_offset, 1, line['name'],
                        get_format({'align': 'center', 'bold': 'True'}) if is_bold else get_format({'align': 'center'}))
                    sheet.write(y_offset, 2, line['total'], 
                        get_format({'num_format': '#,###,0', 'bold': 'True'}) if is_bold else get_format({'num_format': '#,###,0'}))
                    y_offset +=1
            else:
                line_not_receivables = self.get_line_not_receivables(o)
                for line in line_not_receivables:
                    sheet.merge_range(y_offset, 0, y_offset, 1, line.get('name'),
                        get_format({'align': 'center', 'bold': 'True'}) if line.get('bold') == 1 else get_format({'align': 'center'}))
                    sheet.write(y_offset, 2, line.get('total'), 
                        get_format({'num_format': '#,###,0', 'bold': 'True'}) if line.get('bold') == 1 else get_format({'num_format': '#,###,0'}))
                    y_offset +=1
                
                sheet.merge_range(y_offset, 0, y_offset, 1, 'Các khoản phải thu', get_format({'bold': 'True', 'underline': 1}))
                y_offset += 1
                line_receivables = self.get_line_receivables(o)
                for line in line_receivables:
                    sheet.merge_range(y_offset, 0, y_offset, 1, line.get('name'), get_format({'align': 'center'}))
                    sheet.write(y_offset, 2, line.get('total'), get_format({'num_format': '#,###,0'}))
                    y_offset +=1

                sheet.merge_range(y_offset, 0, y_offset, 1, 'Lương còn được nhận', get_format({'bold': 'True', 'color': 'red', 'underline': 1}))
                sheet.write(y_offset, 2, self.get_total(o) , get_format({'num_format': '#,###,0', 'bold': 'True'}))

            
    def get_line_not_receivables(self, o):
        result = []
        sorted_lines = o.line_ids.sorted(key=lambda x: x.salary_rule_id.payslip_no or 999)
        for line in sorted_lines.filtered(lambda x: x.category_id and x.category_id.is_receivables == False and x.salary_rule_id and x.salary_rule_id.code != 'NET'):
            if line.total == 0 and line.code not in ['NC', 'BASIC', 'KPI', 'LNC', 'NET', 'TCONG', 'TTNC', 'TTN']:
                continue
            bold = 1 if line.salary_rule_id.is_bold == True else 0
            result.append({
                'name': line.name,
                'total': line.total,
                'bold': bold 
            })
        return result        

    def get_line_receivables(self, o):
        result = []
        sorted_lines = o.line_ids.sorted(key=lambda x: x.salary_rule_id.payslip_no or 999)
        for line in sorted_lines.filtered(lambda x: x.category_id and x.category_id.is_receivables == True):
            if line.total == 0 and line.code not in ['NC', 'BASIC', 'KPI', 'LNC', 'NET', 'TCONG', 'TTNC', 'TTN']:
                continue
            result.append({
                'name': line.name,
                'total': line.total,
            })
        return result 
    
    def get_total(self, o):
        total = 0
        for line in o.line_ids.filtered(lambda x: x.salary_rule_id and x.salary_rule_id.code == 'NET'):
            total += line.total 
        return total 