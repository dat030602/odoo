# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models
from odoo.modules.module import get_module_resource

import xlsxwriter
import ast
import json
import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
TITLE = 'Sổ tổng hợp bán hàng'

COLUMNS = [
    {"size":  5,                                "name": 'STT'                 , 'field':"no"                               , "type": 'number_c_int'       , "sum": False  },
    {"size": 10,                                "name": 'Mã khách hàng'       , 'field':"partner_code"                     , "type": 'text'               , "sum": False  },
    {"size": 20,                                "name": 'Khách hàng'          , 'field':"partner_name"                     , "type": 'text'               , "sum": False  },
    {"size": 10,  "group": "Bán hàng",          "name": 'DS chưa thuế'        , 'field':"amount_untaxed"                   , "type": 'number_int'         , "sum": True   },
    {"size": 10,  "group": "Bán hàng",          "name": 'Thuế VAT'            , 'field':"amount_tax"                       , "type": 'number_int'         , "sum": True   },
    {"size": 10,  "group": "Bán hàng",          "name": 'DS sau thuế'         , 'field':"amount_total"                     , "type": 'number_int'         , "sum": True   },
    {"size": 10,  "group": "Công nợ",           "name": 'Nợ cũ'               , 'field':"debt_old"                         , "type": 'number_int'         , "sum": True   },
    {"size": 10,  "group": "Công nợ",           "name": 'Thu nợ'              , 'field':"debt_in"                          , "type": 'number_int'         , "sum": True   },
    {"size": 10,  "group": "Công nợ",           "name": 'Nợ cuối'             , 'field':"debt_end"                         , "type": 'number_int'         , "sum": True   },
    {"size": 15,                                "name": 'Nhân viên bán hàng'  , 'field':"user_name"                        , "type": 'text'               , "sum": False  },
    {"size": 8,                                 "name": 'Khu vực'             , 'field':"team_name"                        , "type": 'text'               , "sum": False  },
    {"size": 10,                                "name": 'Ghi chú'             , 'field':"note"                             , "type": 'text'               , "sum": False  },
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

def init_sums():
    sums = {}
    for key in COLUMNS:
        if key.get("sum", False):
            sums[key.get("field")] = 0
    return sums

def update_sums(sums, data):
    for key in COLUMNS:
        if key.get("sum", False):
            sums[key.get("field")] += data.get(key.get("field"), 0)
    return sums

def safe_data(data, key, sub_key="", is_num=False):
    safe_val = 0 if is_num else ""
    value = getattr(data, key, safe_val)
    if sub_key:
        value = getattr(value, sub_key, safe_val)
    return value if value else safe_val

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

class ReportDebtSaleTotalXlsx(models.AbstractModel):
    _name = "report.ccv_report_debt_sale.report_debt_sale_total_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE
    
    def _get_data_export(self, obj):
        """Get organized data for export without partner grouping - similar to production report"""
        count = 0
        lines = []
        grand_totals = init_sums()
        
        lines_obj = obj.line_total_ids
        
        for data in lines_obj:
            count += 1
            vals = {
                "no": count,
                "partner_code":   safe_data(data, "partner_id", "code_contact"),
                "partner_name":   safe_data(data, "partner_id", "name"),
                "user_name":      safe_data(data, "user_id", "name_without_position"),
                "team_name":      safe_data(data, "team_id", "code"),
                "amount_untaxed": safe_data(data, "price_subtotal", is_num=True),
                "amount_tax":     safe_data(data, "price_tax", is_num=True),
                "amount_total":   safe_data(data, "price_total", is_num=True),
                "debt_old":       safe_data(data, "debt_old", is_num=True),
                "debt_in":        safe_data(data, "debt_in", is_num=True),
                "debt_end":       safe_data(data, "debt_end", is_num=True),
                "note": "",
            }

            grand_totals = update_sums(grand_totals, vals)
            replace_zeros(vals)
            lines.append(vals)
            
            # Update grand totals
        replace_zeros(grand_totals)

        return {
            "all_lines": lines,
            "grand_totals": grand_totals
        }

    def add_title(self, sheet, formats, obj):
        # Keep company name and address fixed
        sheet.merge_range("C2:K2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751",formats["company_name"],)
        
        # Keep image insertion as is
        sheet.insert_image("A1",get_module_resource("ccv_bao_cao", "static/src/img", "logo.png"),{"x_offset": 0, "y_offset": 0, "x_scale": 0.22, "y_scale": 0.22},)

        # Calculate the last column letter dynamically
        last_column_letter = chr(65 + len(COLUMNS) - 1)

        # Adjust main title to span all columns
        title_text = TITLE.upper()
        sheet.merge_range(f"A4:{last_column_letter}4", title_text, formats["title_main"])
        sheet.set_row(3, 35)
        
        subtitle = "Từ ngày %s đến ngày %s" % (obj.date_from.strftime("%d/%m/%Y"), obj.date_to.strftime("%d/%m/%Y"))
        sheet.merge_range(f"A5:{last_column_letter}5", subtitle, formats["title_sub"])
        sheet.set_row(4, 20)

    def add_header(self, sheet, formats, obj):
        row_group = 6
        row_detail = 7

        col = 0
        last_group = None
        group_start_col = 0

        for i, column in enumerate(COLUMNS):
            group = column.get("group", "")
            name = column.get("name", "")

            if not group:
                sheet.merge_range(row_group, col, row_detail, col, name, formats["header"])
            else:
                # Ghi tiêu đề con (tên cột)
                sheet.write(row_detail, col, name, formats["header"])

                is_last = (i == len(COLUMNS) - 1)
                next_group = COLUMNS[i + 1].get("group", "") if not is_last else None

                if group != last_group:
                    group_start_col = col

                if group != next_group or is_last:
                    # Merge ngang cho group
                    sheet.merge_range(row_group, group_start_col, row_group, col, group, formats["header"])

            last_group = group
            col += 1

    def add_body(self, sheet, formats, obj):
        lines_data = self._get_data_export(obj)
        prod_row = 8

        # Xác định chỉ số cột đầu tiên có 'sum': True để định vị nhãn "TỔNG CỘNG"
        first_summable_col_idx = -1
        for idx, col_def in enumerate(COLUMNS):
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
            merge_label_col_end_idx = len(COLUMNS) - 1

        # Ghi các dòng dữ liệu chi tiết (không nhóm theo nhà cung cấp)
        all_lines = lines_data.get("all_lines", [])
        for row in all_lines:
            for col_idx, column_def in enumerate(COLUMNS):
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
        for col_idx, column_def in enumerate(COLUMNS):
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
            {"role": "Người Lập", "signer": obj.voter_id.name_without_position if obj.voter_id else ""},
            {"role": "Phòng Kế toán", "signer": obj.chief_finance_id.name_without_position if obj.chief_finance_id else ""},
            {"role": "Thủ trưởng đơn vị", "signer": obj.director_id.name_without_position if obj.director_id else ""},
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
        for obj in objects:
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE,"author": self.env.user.name_without_position,})
            sheet.set_footer('&"Times New Roman"&11Trang &P/&N')
            sheet.set_landscape()
            sheet.set_margins(
                left=0.18,
                right=0.23,
                top=0.32,
                bottom=0.34
            )
            sheet.set_header(margin=0.3)
            sheet.set_footer(margin=0.3)
            sheet.center_horizontally()
            sheet.set_paper(9)
            sheet.fit_to_pages(1, 0)
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)