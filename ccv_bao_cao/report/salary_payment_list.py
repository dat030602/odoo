# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

import xlsxwriter
import ast
import json
import logging

_logger = logging.getLogger(__name__)

def format_workbook(workbook, font_size, font_name="Times New Roman", **kwargs):
    """
    Tạo định dạng Excel linh hoạt bằng xlsxwriter.

    Các tham số chính:
        - font_size (int): Cỡ chữ (bắt buộc)
        - font_name (str): Tên font, mặc định "Times New Roman"
        - align (str): Canh hàng ngang ('left', 'center', 'right', ...)

    Các tham số tùy chọn (qua **kwargs), dùng tên hàm không có 'set_':
        - bold (bool): In đậm (True/False)
        - italic (bool): In nghiêng (True/False)
        - underline (int): Gạch chân (0: không, 1: gạch đơn, 2: đôi)
        - font_color (str): Màu chữ (mã màu hex hoặc tên, ví dụ: 'red' hoặc '#FF0000')
        - num_format (str): Định dạng số, ví dụ: '#,##0', '0.00%', ...
        - text_wrap (bool): Tự động xuống dòng
        - fg_color (str): Màu nền ô
        - bg_color (str): Màu nền nền (ít dùng hơn fg_color)
        - border (int): Viền (0: không, 1: viền mỏng)
        - left, right, top, bottom (int): Viền bên trái/phải/trên/dưới (0/1/2)
        - align (str): Căn hàng ngang ('left', 'center', 'right', 'center_across')
        - valign (str): Căn hàng dọc ('top', 'vcenter', 'bottom')
        - rotation (int): Góc xoay chữ (0-90 hoặc -90)
        - indent (int): Thụt lề
        - shrink (bool): Thu nhỏ để vừa ô
        - locked (bool): Khóa ô (cho bảo vệ sheet)
        - hidden (bool): Ẩn công thức
        - pattern (int): Kiểu họa tiết nền
        - border_color (str): Màu viền
        - left_color, right_color, top_color, bottom_color (str): Màu viền cụ thể
        - font_family (int): Mã font (1: Roman, 2: Swiss, ...)
        - font_charset (int): Mã bộ ký tự (1: Latin, 204: Unicode, ...)
        - theme (int): Màu theo theme (0–11)
        - hyperlink (str): Tạo hyperlink
        - quote_prefix (bool): Giữ nguyên dấu nháy trong chuỗi
        - reading_order (int): 0: L->R, 1: R->L

    Trả về:
        format: Đối tượng format đã cấu hình.
    """
    format = workbook.add_format()

    # Mặc định cơ bản
    format.set_font_name(font_name)
    format.set_font_size(font_size)
    format.set_align('vcenter')

    # Gọi các phương thức động
    for key, value in kwargs.items():
        method_name = f"set_{key}"
        if hasattr(format, method_name):
            getattr(format, method_name)(value)
        else:
            raise ValueError(f"Không tồn tại phương thức: {method_name}")

    return format

def create_formats(workbook):

    return {
        # Titles
        "title_main": format_workbook(workbook, 16, bold=True, align="center"),
        "title_sub": format_workbook(workbook, 12, bold=True, italic=True, text_wrap=True, align='center'),

        # Company
        "company_name": format_workbook(workbook, 13, align="left"),

        # Table Header
        "header": format_workbook(workbook, 11, bold=True, border=1, text_wrap=True, align='center'),

        # Body Text
        "text": format_workbook(workbook, 11.5, border=1, align='center', text_wrap=True),
        "date": format_workbook(workbook, 11.5, border=1, num_format='dd/mm/yyyy', align='center', text_wrap=True),

        # Numbers
        "number_int": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0"),
        "number_float2": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0.00"),
        "number_float3": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0.000"),

        # Totals
        "total_int": format_workbook(workbook, 10, border=1, bold=True, align='right', num_format="#,##0"),
        "total_float2": format_workbook(workbook, 10, border=1, bold=True, align='right', num_format="#,##0.00"),
        "total_float3": format_workbook(workbook, 10, border=1, bold=True, align='right', num_format="#,##0.000"),
        "total_text_bold": format_workbook(workbook, 10, border=1, bold=True, text_wrap=True, align="left"),

        # Description
        "description_bold": format_workbook(workbook, 10, bold=True, text_wrap=True, align="left"),
        "description": format_workbook(workbook, 10, text_wrap=True, align="left"),

        # Signature
        "signature_name": format_workbook(workbook, 12, bold=True, align="center", text_wrap=True, valign="vcenter"),
        "signature_note": format_workbook(workbook, 12, italic=True, align="center", text_wrap=True),
        "signature_date": format_workbook(workbook, 11, italic=True, align="center", text_wrap=True),
    }

def get_evaluated_data(data_dict, key):
    raw_value = data_dict.get(key)
    if raw_value is None:
        return None
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        if not raw_value.strip():
            return raw_value
        try:
            evaluated_value = ast.literal_eval(raw_value)
            if isinstance(evaluated_value, str) and evaluated_value == raw_value:
                pass
            else:
                return evaluated_value
        except (ValueError, SyntaxError) as e:
            pass
        try:
            evaluated_value = json.loads(raw_value)
            return evaluated_value
        except json.JSONDecodeError:
            pass
        return raw_value
    return raw_value

def remove_prefix_from_string(input_string: str):
    if not input_string:
        return ""

    if ' - ' in input_string:
        separator_index = input_string.find(' - ')
        return input_string[separator_index + len(' - '):].strip()
    else:
        return input_string.strip()

class SalaryPaymentList(models.AbstractModel):
    _name = "report.ccv_bao_cao.salary_payment_list"
    _inherit = "report.report_xlsx.abstract"
    _description = "Salary Payment List"  

    
    
    def get_data_export(self, data_raw):
        department_ids = get_evaluated_data(data_raw, 'department_ids')
        advance_salary = get_evaluated_data(data_raw, 'advance_salary')
        month = get_evaluated_data(data_raw, 'month')
        year = get_evaluated_data(data_raw, 'year')
        env_params = self.env['ir.config_parameter'].sudo()
        salary_code = env_params.get_param('ccv_bao_cao.salary_code', False)
        salary_advance_code = env_params.get_param('ccv_bao_cao.salary_advance_code', False)
        code = salary_advance_code if advance_salary else salary_code
        if not code:
            raise UserError("Vui lòng cấu hình Code trong bảng lương!!!")
        
        payslip_runs = self.env['hr.payslip.run'].sudo().search([]).filtered(lambda l:l.date_start.month == month and l.date_start.year == year)
        payslips = self.env['hr.payslip'].sudo().search([('employee_id.department_id','in',department_ids),('payslip_run_id','in', payslip_runs.ids)])
        lines = []
        sum_line = 0
        count = 1
        for payslip in payslips:
            employee_id = payslip.employee_id
            name = remove_prefix_from_string(employee_id.name)
            
            bank_ids = employee_id.sudo().bank_account_id
            
            if advance_salary:
                line_ids = employee_id.env['advance.salary.line'].search([
                    ('employee_id', '=', employee_id.id),
                    ('advance_id.month', '=', str(payslip.date_from.month) if payslip.date_from else str(datetime.now().month)),
                    ('advance_id.year', '=', str(payslip.date_from.year) if payslip.date_from else str(datetime.now().year)),
                ])
                amount = sum(line_ids.mapped('amount'))
            else:
                line_ids = payslip.line_ids.filtered(lambda l:l.code == salary_code)
                amount = sum(line_ids.mapped('total'))
            sum_line += amount
            vals = {
                "no": count,
                "code": employee_id.code if employee_id.code else "",
                "name": name,
                "acc_number": bank_ids.acc_number if bank_ids and bank_ids.acc_number else "TM",
                "bank": bank_ids.bank_id.name if bank_ids and bank_ids.bank_id else "",
                "amount": amount,
                "note": "",
            }
            count += 1
            lines.append(vals)
        return {
            "sum": sum_line,
            "lines": lines,
        }
    
    def add_title(self, sheet, formats, data_raw):
        month = get_evaluated_data(data_raw, 'month')
        formatted_month = f"{month:02d}"
        year = get_evaluated_data(data_raw, 'year')
        advance_salary = get_evaluated_data(data_raw, 'advance_salary')
        sheet.merge_range("C2:G2", "Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751", formats["company_name"])
        sheet.merge_range("C3:G3", "23 Lô B, Đường số 1, P. Phú Thuận, Q.7", formats["company_name"])
        sheet.insert_image('A1', get_module_resource('ccv_bao_cao', 'static/src/img', 'logo.png'), 
                        {'x_offset': 0, 'y_offset': 0, "x_scale": 0.22, "y_scale": 0.22})

        title_text = "DANH SÁCH CHI LƯƠNG%s CNSX THÁNG %s/%s" % ('' if not advance_salary else ' TẠM ỨNG', formatted_month,year)
        sheet.merge_range("A4:G4", title_text, formats["title_main"])
        sheet.set_row(3, 35)
        sheet.merge_range("A5:G5", "(Kèm  theo Lệnh chi/UNC ... Ngày ... tháng ... năm ...)", formats["title_sub"])
        sheet.set_row(4, 20)

    def add_header(self, sheet, formats, data_raw):
        advance_salary = get_evaluated_data(data_raw, 'advance_salary')
        w_row_header = 6
        simple_headers = [
            "STT",
            "Mã nhân viên",
            "Tên nhân viên",
            "Số tài khoản",
            "Ngân hàng",
            "Số tiền%s" % ('' if not advance_salary else 'tạm ứng'),
            "Nội dung",
        ]
        for i, header in enumerate(simple_headers):
            sheet.write(w_row_header,i, header,formats["header"])

    def add_body(self, sheet, formats, data_raw):
        columns = [
            {"size": 5, "name": "no", "is_num": False},
            {"size": 12, "name": "code", "is_num": False},
            {"size": 25, "name": "name", "is_num": False},
            {"size": 15, "name": "acc_number", "is_num": False},
            {"size": 20, "name": "bank", "is_num": False},
            {"size": 10, "name": "amount", "is_num": True},
            {"size": 20, "name": "note", "is_num": False},
        ]

        lines = self.get_data_export(data_raw)

        prod_row = 7
        for row in lines.get('lines'):
            for col, column in enumerate(columns):
                sheet.set_column(col, col, column["size"])
                fmt = formats["number_int"] if column["is_num"] else formats["text"]
                sheet.write(prod_row, col, row[column["name"]], fmt)
            prod_row += 1

        # Tổng cộng
        prod_row += 1
        sheet.merge_range(f"A{prod_row}:E{prod_row}", "TỔNG CỘNG", formats["total_text_bold"])
        sheet.write(prod_row - 1, 5, lines.get('sum'), formats["total_int"])
        sheet.write(prod_row - 1, 6, "", formats["text"])

    def _get_sign_name(self, id):
        if not id:
            return ""
        user = self.env['res.users'].browse(id)
        return user.name_without_position if user else ""

    def add_signatures(self, sheet, formats, data_raw):
        row = sheet.dim_rowmax + 3
        sheet.merge_range(f"E{row}:G{row}", "Ngày ..... tháng ..... năm .........", formats["signature_date"])

        row += 1
        roles = ["Người Lập", "Phòng HCNS", "Phòng Kế toán", "Thủ trưởng đơn vị"]
        for i in range(len(roles)):
            col_from = chr(65 + i * 2)
            col_to = chr(66 + i * 2)
            sheet.merge_range(f"{col_from}{row}:{col_to}{row}", roles[i], formats["signature_name"])
        row += 5
        signers = [
            self._get_sign_name(get_evaluated_data(data_raw, 'voter_id')),
            self._get_sign_name(get_evaluated_data(data_raw, 'human_resources_dept_id')),
            self._get_sign_name(get_evaluated_data(data_raw, 'chief_finance_id')),
            self._get_sign_name(get_evaluated_data(data_raw, 'director_id')),
        ]
        for i in range(len(signers)):
            col_from = chr(65 + i * 2)
            col_to = chr(66 + i * 2)
            sheet.merge_range(f"{col_from}{row}:{col_to}{row}", signers[i], formats["signature_name"])

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, data_raw, objects):
        sheet = workbook.add_worksheet("DANH SÁCH CHI LƯƠNG CNSX THÁNG 04/2025")
        workbook.set_properties({'title': 'DANH SÁCH CHI LƯƠNG CNSX', 'author': self.env.user.display_name})
        sheet.set_landscape()

        formats = create_formats(workbook)
        self.add_title(sheet, formats, data_raw)
        self.add_header(sheet, formats, data_raw)
        self.add_body(sheet, formats, data_raw)
        self.add_signatures(sheet, formats, data_raw)
