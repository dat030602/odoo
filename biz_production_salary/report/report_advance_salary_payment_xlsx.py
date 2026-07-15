# -*- coding: utf-8 -*-
from odoo import models, _
from datetime import datetime

class ReportAdvanceSalaryPayment(models.AbstractModel):
    _name = 'report.biz_production_salary.report_advance_salary_payment_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Advance Salary Payment Excel Report'

    def generate_xlsx_report(self, workbook, data, details):
        company = self.env.company
        
        table_border_header = workbook.add_format({
            'font_name': 'Times New Roman', 'font_size': 12,
            'align': 'center', 'valign': 'vcenter', 'border': True, 'bold': True, 'text_wrap': True,
        })
        table_border_body = workbook.add_format({
            'font_name': 'Times New Roman', 'font_size': 12,
            'align': 'left', 'valign': 'vcenter', 'border': True
        })
        table_border_body_center = workbook.add_format({
            'font_name': 'Times New Roman', 'font_size': 12,
            'align': 'center', 'valign': 'vcenter', 'border': True
        })
        table_border_body_amount = workbook.add_format({
            'font_name': 'Times New Roman', 'font_size': 12,
            'align': 'right', 'valign': 'vcenter', 'border': True, 'num_format': '#,##0'
        })
        title_format = workbook.add_format({
            'font_name': 'Times New Roman', 'font_size': 14,
            'align': 'center', 'valign': 'vcenter', 'bold': True
        })
        bold_format = workbook.add_format({
            'font_name': 'Times New Roman', 'font_size': 12, 'bold': True
        })

        for o in details:
            sheet = workbook.add_worksheet(_('Tam Ung Luong'))
            
            # Column widths
            sheet.set_column(0, 0, 5)   # STT
            sheet.set_column(1, 1, 15)  # Mã NV
            sheet.set_column(2, 2, 35)  # Họ tên
            sheet.set_column(3, 3, 25)  # Chức danh
            sheet.set_column(4, 4, 20)  # Số TK
            sheet.set_column(5, 5, 30)  # Ngân hàng
            sheet.set_column(6, 6, 20)  # Số tiền
            sheet.set_column(7, 7, 25)  # Ghi chú

            y_offset = 0
            sheet.write(y_offset, 0, company.name, bold_format)
            y_offset += 2
            
            # Title
            title_str = 'DANH SÁCH THANH TOÁN TẠM ỨNG LƯƠNG'
            if o.month and o.year:
                title_str += f' THÁNG {o.month}/{o.year}'
            sheet.merge_range(y_offset, 0, y_offset, 7, title_str, title_format)
            y_offset += 2

            # Headers
            sheet.set_row(y_offset, 30)
            headers = ['STT', 'Mã nhân viên', 'Họ và tên', 'Chức danh', 'Số tài khoản', 'Ngân hàng', 'Số tiền tạm ứng', 'Ghi chú']
            for col_num, header_str in enumerate(headers):
                sheet.write(y_offset, col_num, header_str, table_border_header)
            
            y_offset += 1
            stt = 1
            total_amount = 0
            
            # Print lines
            for line in o.line_ids:
                emp = line.employee_id
                sheet.write(y_offset, 0, stt, table_border_body_center)
                sheet.write(y_offset, 1, emp.code or '', table_border_body_center)
                sheet.write(y_offset, 2, emp.name or '', table_border_body)
                sheet.write(y_offset, 3, emp.job_title or '', table_border_body)
                sheet.write(y_offset, 4, emp.bank_account_id and emp.bank_account_id.acc_number or '', table_border_body_center)
                sheet.write(y_offset, 5, emp.bank_account_id and emp.bank_account_id.bank_id and emp.bank_account_id.bank_id.name or '', table_border_body)
                sheet.write(y_offset, 6, line.amount or 0, table_border_body_amount)
                sheet.write(y_offset, 7, '', table_border_body)
                total_amount += (line.amount or 0)
                y_offset += 1
                stt += 1

            # Total line
            sheet.merge_range(y_offset, 0, y_offset, 5, 'Tổng cộng', workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'align': 'right', 'valign': 'vcenter', 'border': True, 'bold': True}))
            sheet.write(y_offset, 6, total_amount, workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'align': 'right', 'valign': 'vcenter', 'border': True, 'bold': True, 'num_format': '#,##0'}))
            sheet.write(y_offset, 7, '', table_border_body)
            y_offset += 2

            # Footer
            sheet.merge_range(y_offset, 4, y_offset, 7, f'Ngày {datetime.now().day:02d} tháng {datetime.now().month:02d} năm {datetime.now().year}', workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center', 'valign': 'vcenter'}))
            y_offset += 1
            sheet.merge_range(y_offset, 0, y_offset, 2, 'NGƯỜI LẬP', workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 4, y_offset, 7, 'GIÁM ĐỐC', workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'bold': True, 'align': 'center'}))
