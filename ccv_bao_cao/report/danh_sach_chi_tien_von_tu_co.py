# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models
from odoo.modules.module import get_module_resource

import xlsxwriter
import ast
import json
import logging

_logger = logging.getLogger(__name__)
TITLE = 'Danh sách chi tiền vốn tự có'

BASE_COLUMNS = [
    {"size": 5, "name": 'STT', 'field': "no", "type": 'number_c_int', "sum": False},
    {"size": 12, "name": 'Mã đối tác', 'field': "partner_code", "type": 'text', "sum": False},
    {"size": 20, "name": 'Tên đối tác', 'field': "partner_name", "type": 'text', "sum": False},
    {"size": 25, "name": 'Nội dung', 'field': "reference", "type": 'text', "sum": False},
    {"size": 10, "name": 'Ngày', 'field': "date", "type": 'date', "sum": False},
    {"size": 12.7, "name": 'Số phiếu', 'field': "note", "type": 'text', "sum": False},
    {"size": 12, "name": 'Số tiền', 'field': "amount_total", "type": 'number_int', "sum": True},
    {"size": 8, "name": 'Tiền tệ', 'field': "currency_name", "type": 'text', "sum": False},
]

PKD_SIGN_COLUMN = {"size": 15, "name": 'PKD Ký xác nhận', 'field': "pkd_sign", "type": 'text', "sum": False}

def get_columns(partner_payment_type):
    """Get columns based on partner_payment_type"""
    columns = BASE_COLUMNS.copy()
    if partner_payment_type == 'customer':
        columns.append(PKD_SIGN_COLUMN)
    return columns

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
        except (ValueError, SyntaxError):
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

def init_sums(columns):
    sums = {}
    for key in columns:
        if key.get("sum", False):
            sums[key.get("field")] = 0
    return sums

def update_sums(sums, data, lines, columns, is_total=False):
    for key in columns:
        if key.get("sum", False):
            if not is_total and key.get("value_end", False):
                sums[key.get("field")] = lines.mapped(key.get("field"))[-1]
                continue
            sums[key.get("field")] += data.get(key.get("field"), 0)
    return sums

def safe_data(data, key, sub_key="", is_num=False):
    safe_val = 0 if is_num else ""
    value = getattr(data, key, safe_val)
    if sub_key:
        value = getattr(value, sub_key, safe_val)
    if is_num and isinstance(value, (int, float)):
        return value
    return value

def create_formats(workbook):
    return {
        # Titles
        "title_main": format_workbook(workbook, 16, bold=True, align="center", text_wrap=True),
        "title_sub": format_workbook(workbook, 12, bold=True, italic=True, text_wrap=True, align='center'),

        # Company
        "company_name": format_workbook(workbook, 13, align="left"),

        # Table Header
        "header": format_workbook(workbook, 11, bold=True, border=1, text_wrap=True, align='center'),

        # Body Text
        "text": format_workbook(workbook, 11.5, border=1, align='center', text_wrap=True),
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

class danh_sach_chi_tien_von_tu_co(models.AbstractModel):
    _name = "report.ccv_bao_cao.danh_sach_chi_tien_von_tu_co"
    _inherit = "report.report_xlsx.abstract"
    _description = "Danh sách chi tiền vốn tự có"

    def _get_data_export(self, obj):
        """Get organized data for export with direct data querying"""
        lines = []
        columns = get_columns(obj.partner_payment_type)
        grand_totals = init_sums(columns)
        
        # Query data directly from the object's lines
        lines_obj = obj.beta_line7_ids.sudo()
        
        count = 0
        for data in lines_obj:
            count += 1
            vals = {
                "no": count,
                "partner_code": safe_data(data, "partner_id", sub_key="code_contact"),
                "partner_name": safe_data(data, "partner_id", sub_key="name"),
                "reference": safe_data(data, "reference"),
                "date": safe_data(data, "date"),
                "note": safe_data(data, "note"),
                "amount_total": safe_data(data, "amount_total", is_num=True),
                "currency_name": safe_data(data, "currency_id", sub_key="display_name"),
            }
            
            # Only include pkd_sign if partner_payment_type is 'customer'
            if obj.partner_payment_type == 'customer':
                vals["pkd_sign"] = safe_data(data, "pkd_sign")
            
            lines.append(vals)
            
            # Update grand totals
            grand_totals = update_sums(grand_totals, vals, lines_obj, columns, is_total=True)

        return {
            "lines": lines,
            "grand_totals": grand_totals,
            "columns": columns,
        }

    def add_title(self, sheet, formats, obj):
        """Add title section to the sheet"""
        sheet.merge_range("C2:H2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751", formats["company_name"])
        sheet.insert_image('A1', get_module_resource('ccv_bao_cao', 'static/src/img', 'logo.png'), {'x_offset': 0, 'y_offset': 0,"x_scale": 0.2, "y_scale": 0.2})

        # Calculate the last column letter dynamically
        columns = get_columns(obj.partner_payment_type)
        last_column_letter = chr(65 + len(columns) - 1)

        if obj.partner_payment_type == 'customer':
            title = "DANH SÁCH THU TIỀN"
            if obj.report_type == 'team' and obj.team_id and obj.team_id.report_name:
                title += '\n'
                title += obj.team_id.report_name.upper()
        else:
            title = "DANH SÁCH CHI TIỀN VỐN TỰ CÓ"
        
        sheet.merge_range(f"A4:{last_column_letter}4", title, formats["title_main"])
        sheet.set_row(3, 35)
        title = "Từ ngày %s đến hết ngày %s" % (obj.date_from.strftime("%d/%m/%Y"), obj.date_to.strftime("%d/%m/%Y"))
        sheet.merge_range(f"A5:{last_column_letter}5", title, formats["title_sub"])
        sheet.set_row(4, 20)

    def add_header(self, sheet, formats, obj):
        """Add header section to the sheet"""
        # Generate title_partner and title_money based on object properties
        if obj.partner_payment_type == 'customer':
            title_partner = "khách hàng"
            title_money = "thanh toán"
        else:
            title_partner = "nhà cung cấp"
            title_money = "ký kết"
        
        columns = get_columns(obj.partner_payment_type)
        w_row_header = 6
        for col_idx, column in enumerate(columns):
            name = column.get("name", "")
            if name == "Mã đối tác":
                name = f"Mã {title_partner}"
            elif name == "Tên đối tác":
                name = f"Tên {title_partner}"
            elif name == "Số tiền":
                name = f"Số tiền {title_money}"
            
            sheet.merge_range(f"{chr(65 + col_idx)}{w_row_header}:{chr(65 + col_idx)}{w_row_header+1}", name, formats["header"])

    def add_body(self, sheet, formats, obj):
        """Add body content to the sheet"""
        lines_data = self._get_data_export(obj)
        columns = lines_data.get("columns", [])
        currency_id = obj.currency_id if hasattr(obj, 'currency_id') else 23
        
        # Tạo format số động dựa trên currency_id
        if currency_id == 23:
            formats["number_dynamic"] = formats["number_int"]
            formats["total_dynamic"] = formats["total_int"]
        else:
            formats["number_dynamic"] = formats["number_float2"]
            formats["total_dynamic"] = formats["total_float2"]

        prod_row = 7

        # Xác định chỉ số cột đầu tiên có 'sum': True để định vị nhãn "TỔNG CỘNG"
        first_summable_col_idx = -1
        for idx, col_def in enumerate(columns):
            if col_def['sum']:
                first_summable_col_idx = idx
                break
        
        # Chỉ số cột cuối cùng để gộp ô cho nhãn "TỔNG CỘNG"
        merge_label_col_end_idx = 0 
        if first_summable_col_idx != -1:
            # Gộp đến cột ngay trước cột summable đầu tiên
            merge_label_col_end_idx = max(0, first_summable_col_idx - 1)
        else: 
            # Nếu không có cột nào summable, gộp qua tất cả các cột
            merge_label_col_end_idx = len(columns) - 1

        # Ghi các dòng dữ liệu chi tiết
        lines = lines_data.get("lines", [])
        for row in lines:
            for col_idx, column_def in enumerate(columns):
                sheet.set_column(col_idx, col_idx, column_def.get('size', 10))
                fmt = formats[column_def.get('type', 'text')]
                
                field_name = column_def.get('field')
                cell_value = row.get(field_name)

                # Xử lý đặc biệt cho kiểu ngày/thời gian
                if column_def.get('type') == 'date' and isinstance(cell_value, datetime):
                    cell_value = cell_value.date()
                elif column_def.get('type') == 'datetime' and isinstance(cell_value, datetime):
                    pass # xlsxwriter tự xử lý đối tượng datetime với num_format

                sheet.write(prod_row, col_idx, cell_value, fmt)
            prod_row += 1
        
        # --- Phần Tổng Cộng Chung (Grand Total) ---
        grand_totals = lines_data.get("grand_totals", {})
        
        # Nhãn "TỔNG CỘNG"
        sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                          "TỔNG CỘNG", formats["total_text_bold"])
        
        # Ghi tổng của từng cột summable
        for col_idx, column_def in enumerate(columns):
            if column_def['sum']:
                field_name = column_def.get('field')
                sum_value = grand_totals.get(field_name, 0)
                
                # Xác định định dạng tổng phù hợp
                total_fmt_key = column_def['type'].replace('number', 'total')
                fmt = formats.get(total_fmt_key, formats["total_int"]) 

                sheet.write(prod_row, col_idx, sum_value, fmt)
            elif col_idx > merge_label_col_end_idx:
                sheet.write(prod_row, col_idx, "", formats["text"])
        prod_row += 1

    def add_signatures(self, sheet, formats, obj):
        """Add signature section to the sheet"""
        row = sheet.dim_rowmax + 3

        columns = get_columns(obj.partner_payment_type)
        last_column_index = len(columns) - 1
        total_columns = len(columns) 

        date_merge_start_col_idx = max(0, last_column_index - 2)
        date_merge_end_col_idx = last_column_index

        date_merge_start_col_letter = chr(65 + date_merge_start_col_idx)
        date_merge_end_col_letter = chr(65 + date_merge_end_col_idx)

        sheet.merge_range(f"{date_merge_start_col_letter}{row}:{date_merge_end_col_letter}{row}", "Ngày ..... tháng ..... năm .........", formats["signature_date"])

        row += 1 

        signature_blocks = [
            {"role": "Người Lập Biểu", "signer": obj.voter_id.name_without_position if obj.voter_id else ""},
            {"role": "Kế Toán Trưởng", "signer": obj.chief_acc_id.name_without_position if obj.chief_acc_id else ""},
            {"role": "Thủ trưởng đơn vị", "signer": obj.unit_heads_id.name_without_position if obj.unit_heads_id else ""},
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
            
        row += 1 

        current_col_idx = 0
        for i, block in enumerate(signature_blocks):
            col_start_idx = current_col_idx
            if i == num_signature_blocks - 1:
                col_end_idx = last_column_index
            else:
                col_end_idx = col_start_idx + block_width - 1

            col_from_letter = chr(65 + col_start_idx)
            col_to_letter = chr(65 + col_end_idx)

            signature_note = "(Ký, họ tên)"
            if i == num_signature_blocks - 1:
                signature_note = "(Ký, họ tên, đóng dấu)"
            
            sheet.merge_range(f"{col_from_letter}{row}:{col_to_letter}{row}", signature_note, formats["signature_note"])

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

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, data, objects):
        """Generate XLSX report using the new structure"""
        for obj in self.env['alpha.report'].browse(objects.ids):
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE, "author": self.env.user.display_name})
            sheet.set_footer('&"Times New Roman"&11Trang &P/&N')
            sheet.set_landscape()
            formats = create_formats(workbook)
            
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)
