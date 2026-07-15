# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

import xlsxwriter
import ast
import json
import logging
import re
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)
TITLE = 'BẢNG TỔNG HỢP TÍNH HOA HỒNG THEO SẢN LƯỢNG CHO CBCNV PHÒNG KINH DOANH'


COLUMNS = [
    {"size":  5,  "name": 'STT'                     , 'field':"no"                        , "type": 'number_c_int'      , "sum": False  },
    {"size": 30,  "name": 'Nhân viên'               , 'field':"employee_name"             , "type": 'text'              , "sum": False  },
    {"size": 15,  "name": 'Kế hoạch'                , 'field':"planned_quantity"          , "type": 'number_float3'     , "sum": True   },
    {"size": 15,  "name": 'Doanh số'                , 'field':"sales_quantity"            , "type": 'number_float3'     , "sum": True   },
    {"size": 20,  "name": 'Số lượng tính hoa hồng'  , 'field':"commission_quantity"       , "type": 'number_float3'     , "sum": True   },
    {"size": 18,  "name": 'Doanh thu'               , 'field':"revenue_amount"            , "type": 'number_int'        , "sum": True   },
    {"size": 18,  "name": 'Doanh thu tiền về'       , 'field':"cash_revenue_amount"       , "type": 'number_int'        , "sum": True   },
    {"size": 18,  "name": 'Hoa hồng'                , 'field':"commission_amount"         , "type": 'number_int'        , "sum": True   },
]

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
        "text": format_workbook(workbook, 11.5, border=1, align='left', text_wrap=True),
        "date": format_workbook(workbook, 11.5, border=1, num_format='dd/mm/yyyy', align='center', text_wrap=True),
        "datetime": format_workbook(workbook, 11.5, border=1, num_format='dd/mm/yyyy hh:mm:ss', align='center', text_wrap=True),

        # Numbers
        "number_int": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0"),
        "number_float2": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0.00"),
        "number_float3": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0.000"),
        "number_c_int": format_workbook(workbook, 10, border=1, align='center', num_format="#,##0"),
        "number_c_float2": format_workbook(workbook, 10, border=1, align='center', num_format="#,##0.00"),
        "number_c_float3": format_workbook(workbook, 10, border=1, align='center', num_format="#,##0.000"),

        # Totals
        "total_int": format_workbook(workbook, 10, border=1, bold=True, align='right', num_format="#,##0"),
        "total_float2": format_workbook(workbook, 10, border=1, bold=True, align='right', num_format="#,##0.00"),
        "total_float3": format_workbook(workbook, 10, border=1, bold=True, align='right', num_format="#,##0.000"),
        "total_c_int": format_workbook(workbook, 10, border=1, bold=True, align='center', num_format="#,##0"),
        "total_c_float2": format_workbook(workbook, 10, border=1, bold=True, align='center', num_format="#,##0.00"),
        "total_c_float3": format_workbook(workbook, 10, border=1, bold=True, align='center', num_format="#,##0.000"),
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


class RpSalesCommissionEmployeeReport(models.AbstractModel):
    _name = "report.biz_kpi_business_salary.rp_sales_commission_employee"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE
    
    def _init_sum(self):
        """Khởi tạo dictionary để tính tổng dựa trên cấu hình COLUMNS."""
        return {col['field']: 0 for col in COLUMNS if col.get('sum')}
    
    def _get_data_export(self, obj):
        """Lấy dữ liệu từ salary.sales.commission.employee"""
        # Lấy tất cả các bản ghi commission employee liên quan đến summary này
        employee_commissions = self.env['salary.sales.commission.employee'].search([
            ('summary_id', '=', obj.id)
        ], order='employee_id')
        
        lines_data = []
        totals = self._init_sum()
        
        for idx, commission in enumerate(employee_commissions, start=1):
            line_data = {
                "no": idx,
                "employee_name": commission.employee_id.name or '',
                "planned_quantity": commission.planned_quantity or 0,
                "sales_quantity": commission.sales_quantity or 0,
                "commission_quantity": commission.commission_quantity or 0,
                "revenue_amount": commission.revenue_amount or 0,
                "cash_revenue_amount": commission.cash_revenue_amount or 0,
                "commission_amount": commission.commission_amount or 0,
            }
            lines_data.append(line_data)
            
            # Cộng vào tổng các field có sum=True
            for key in totals.keys():
                totals[key] += line_data.get(key, 0)
        
        # Thay thế giá trị 0 bằng chuỗi rỗng cho hiển thị đẹp hơn
        def replace_zeros(d):
            for k, v in d.items():
                if isinstance(v, dict):
                    replace_zeros(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            replace_zeros(item)
                elif v == 0:
                    d[k] = ""
        
        replace_zeros({"lines": lines_data, "totals": totals})
        
        return {
            "lines": lines_data,
            "totals": totals
        }

    def add_title(self, sheet, formats, obj):
        # Keep company name and address fixed
        sheet.merge_range("C2:G2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751",formats["company_name"],)
        sheet.merge_range("C3:G3", "23 Lô B, Đường số 1, P. Phú Thuận, Q.7", formats["company_name"])
        
        # Keep image insertion as is
        try:
            sheet.insert_image("A1",get_module_resource("ccv_bao_cao", "static/src/img", "logo.png"),{"x_offset": 0, "y_offset": 0, "x_scale": 0.22, "y_scale": 0.22},)
        except:
            pass

        # Calculate the last column letter dynamically
        last_column_letter = chr(65 + len(COLUMNS) - 1)

        # Adjust main title to span all columns
        title_text = TITLE.upper()
        sheet.merge_range(f"A4:{last_column_letter}4", title_text, formats["title_main"])
        sheet.set_row(3, 35)
        
        # Thêm thông tin tháng/năm
        month_names = {
            '1': 'Tháng 1', '2': 'Tháng 2', '3': 'Tháng 3', '4': 'Tháng 4',
            '5': 'Tháng 5', '6': 'Tháng 6', '7': 'Tháng 7', '8': 'Tháng 8',
            '9': 'Tháng 9', '10': 'Tháng 10', '11': 'Tháng 11', '12': 'Tháng 12'
        }
        month_name = month_names.get(str(obj.month), '')
        period_text = f"{month_name} năm {obj.year}" if month_name and obj.year else ""
        if period_text:
            sheet.merge_range(f"A5:{last_column_letter}5", period_text, formats["title_sub"])
            sheet.set_row(4, 25)

    def add_header(self, sheet, formats, obj):
        row = 5 if obj.month and obj.year else 5
        
        # Điều chỉnh nếu có dòng tháng/năm
        if obj.month and obj.year:
            row = 6

        col = 0
        for column in COLUMNS:
            name = column.get("name", "")
            sheet.write(row, col, name, formats["header"])
            sheet.set_column(col, col, column.get('size', 10))
            col += 1

    def add_body(self, sheet, formats, obj):
        data = self._get_data_export(obj)
        lines_data = data.get("lines", [])
        totals = data.get("totals", {})
        
        prod_row = 6 if obj.month and obj.year else 6
        
        # Điều chỉnh nếu có dòng tháng/năm
        if obj.month and obj.year:
            prod_row = 7

        # Xác định chỉ số cột đầu tiên có 'sum': True để định vị nhãn "TỔNG CỘNG"
        first_summable_col_idx = -1
        for idx, col_def in enumerate(COLUMNS):
            if col_def['sum']:
                first_summable_col_idx = idx
                break
        
        # Chỉ số cột cuối cùng để gộp ô cho nhãn "TỔNG CỘNG"
        merge_label_col_end_idx = 1  # Gộp từ STT đến Nhân viên
        if first_summable_col_idx != -1:
            merge_label_col_end_idx = max(1, first_summable_col_idx - 1)

        # Ghi dữ liệu từng nhân viên
        for line in lines_data:
            for col_idx, column_def in enumerate(COLUMNS):
                field_name = column_def.get('field')
                cell_value = line.get(field_name)
                fmt = formats[column_def.get('type', 'text')]
                
                # Xử lý đặc biệt cho kiểu ngày/thời gian
                if column_def.get('type') == 'date' and isinstance(cell_value, datetime):
                    cell_value = cell_value.date()
                elif column_def.get('type') == 'datetime' and isinstance(cell_value, datetime):
                    pass # xlsxwriter tự xử lý đối tượng datetime với num_format
                
                sheet.write(prod_row, col_idx, cell_value, fmt)
            prod_row += 1
        
        # Ghi dòng tổng cộng
        sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                          "TỔNG CỘNG", formats["total_text_bold"])
        
        # Ghi tổng của từng cột summable
        for col_idx, column_def in enumerate(COLUMNS):
            if column_def['sum']:
                field_name = column_def.get('field')
                sum_value = totals.get(field_name, 0)
                
                # Xác định định dạng tổng phù hợp
                total_fmt_key = column_def['type'].replace('number', 'total')
                # Dự phòng nếu định dạng 'total' cụ thể không tồn tại
                fmt = formats.get(total_fmt_key, formats["total_int"]) 

                sheet.write(prod_row, col_idx, sum_value, fmt)
            elif col_idx > merge_label_col_end_idx: # Điền ô trống cho các cột không summable sau nhãn
                sheet.write(prod_row, col_idx, "", formats["text"])
        
        # Đặt height = 30 cho dòng tổng cộng
        sheet.set_row(prod_row)

    def add_signatures(self, sheet, formats, obj):
        row = sheet.dim_rowmax + 3

        last_column_index = len(COLUMNS) - 1
        total_columns = len(COLUMNS) 

        date_merge_start_col_idx = max(0, last_column_index - 2)
        date_merge_end_col_idx = last_column_index

        date_merge_start_col_letter = chr(65 + date_merge_start_col_idx)
        date_merge_end_col_letter = chr(65 + date_merge_end_col_idx)

        sheet.merge_range(f"{date_merge_start_col_letter}{row}:{date_merge_end_col_letter}{row}", "Ngày ..... tháng ..... năm .........", formats["signature_date"])

        row += 1 

        signature_blocks = [
            {"role": "Người lập", "signer": obj.voter_id.name_without_position or obj.voter_id.name or ''},
            {"role": "Phòng kinh doanh", "signer": obj.lead_sale_id.name_without_position or obj.lead_sale_id.name or ''},
            {"role": "Phòng kế toán", "signer": obj.chief_finance_id.name_without_position or obj.chief_finance_id.name or ''},
            {"role": "Ban lãnh đạo", "signer": obj.director_id.name_without_position or obj.director_id.name or ''},
        ]

        num_signature_blocks = len(signature_blocks)
        
        block_width = max(1, total_columns // num_signature_blocks)

        current_col_idx = 0
        for i, block in enumerate(signature_blocks):
            col_start_idx = current_col_idx
            if i == num_signature_blocks - 1:
                col_end_idx = last_column_index
            else:
                col_end_idx = col_start_idx + block_width - 1

            col_from_letter = chr(65 + col_start_idx)
            col_to_letter = chr(65 + col_end_idx)

            sheet.merge_range(f"{col_from_letter}{row}:{col_to_letter}{row}", block["role"], formats["signature_name"])

            current_col_idx = col_end_idx + 1
            
        row += 5 

        current_col_idx = 0
        for i, block in enumerate(signature_blocks):
            col_start_idx = current_col_idx
            if i == num_signature_blocks - 1:
                col_end_idx = last_column_index
            else:
                col_end_idx = col_start_idx + block_width - 1

            col_from_letter = chr(65 + col_start_idx)
            col_to_letter = chr(65 + col_end_idx)

            sheet.merge_range(f"{col_from_letter}{row}:{col_to_letter}{row}", block["signer"], formats["signature_name"])

            current_col_idx = col_end_idx + 1

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, obj, objects):
        for obj in objects:
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE,"author": self.env.user.name_without_position if hasattr(self.env.user, 'name_without_position') else self.env.user.name,})
            sheet.set_landscape()
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)

