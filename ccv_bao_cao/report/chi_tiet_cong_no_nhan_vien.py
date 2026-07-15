# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models
from odoo.modules.module import get_module_resource

import xlsxwriter
import ast
import json
import logging

_logger = logging.getLogger(__name__)
TITLE = 'Chi tiết công nợ nhân viên'

COLUMNS = [
    {"size":  5,                                "name": 'STT'                , 'field':"no"                               , "type": 'number_c_int'       , "sum": False  },
    {"size": 10,                                "name": 'Ngày chứng từ'      , 'field':"date"                             , "type": 'date'               , "sum": False  },
    {"size": 15,                                "name": 'Số chứng từ'        , 'field':"move_id"                          , "type": 'text'               , "sum": False  },
    {"size": 8,                                 "name": 'Mã phiếu'           , 'field':"reference"                        , "type": 'text'               , "sum": False  },
    {"size": 20,                                "name": 'Diễn giải'          , 'field':"note"                             , "type": 'text'               , "sum": False  },
    {"size": 10,                                "name": 'Tài khoản đối ứng'  , 'field':"account_dest_id"                  , "type": 'text'               , "sum": False  },
    {"size": 7,                                 "name": 'Số lượng'           , 'field':"product_uom_qty"                  , "type": 'number_float3'      , "sum": True  },
    {"size": 10,                                "name": 'Đơn giá'            , 'field':"price_unit"                       , "type": 'number_int'         , "sum": False  },
    {"size": 10,  "group": "Phát sinh",         "name": 'Nợ'                 , 'field':"debit"                            , "type": 'number_int'         , "sum": True  },
    {"size": 10,  "group": "Phát sinh",         "name": 'Có'                 , 'field':"credit"                           , "type": 'number_int'         , "sum": True  },
    {"size": 10,  "group": "Số dư",             "name": 'Nợ'                 , 'field':"end_debit"                        , "type": 'number_int'         , "sum": True , "value_end": True  },
    {"size": 10,  "group": "Số dư",             "name": 'Có'                 , 'field':"end_credit"                       , "type": 'number_int'         , "sum": True , "value_end": True  },
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

def update_sums(sums, data, lines, is_total=False):
    for key in COLUMNS:
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

class chi_tiet_cong_no_nhan_vien(models.AbstractModel):
    _name = "report.ccv_bao_cao.chi_tiet_cong_no_nhan_vien"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE  
    
    def _get_data_export(self, obj):
        """Get organized data for export with grouping by employee"""
        grouped = {}
        grand_totals = init_sums()
        
        lines_obj = obj.line3_ids.sudo()
        partner_ids = lines_obj.mapped("partner_id")
        
        for partner_id in partner_ids:
            count = 0
            line_ids = lines_obj.filtered(lambda line: line.partner_id.id == partner_id.id)
            if line_ids:
                lines = []
                sums = init_sums()
                
                for data in line_ids:
                    count += 1
                    vals = {
                        "no": count,
                        "partner_name":       safe_data(partner_id, "name"),
                        "date":               safe_data(data, "date"),
                        "move_id":            safe_data(data, "move_id", sub_key="name"),
                        "reference":          safe_data(data, "reference"),
                        "note":               safe_data(data, "note"),
                        "account_dest_id":    safe_data(data, "account_dest_id", sub_key="code"),
                        "product_uom_qty":    safe_data(data, "product_uom_qty", is_num=True),
                        "price_unit":         safe_data(data, "price_unit", is_num=True),
                        "debit":              safe_data(data, "debit", is_num=True),
                        "credit":             safe_data(data, "credit", is_num=True),
                        "end_debit":          safe_data(data, "end_debit", is_num=True),
                        "end_credit":         safe_data(data, "end_credit", is_num=True),
                    }
                    lines.append(vals)
                    
                    # Update sums
                    sums = update_sums(sums, vals, line_ids)
                
                # Update grand totals
                grand_totals = update_sums(grand_totals, sums, line_ids, is_total=True)
                
                vals = {
                    partner_id.name: {
                        "lines": lines,
                        "sums": sums
                    },
                }
                grouped.update(vals)

        replace_zeros(grouped)
        replace_zeros(grand_totals)

        return {
            "grouped": grouped,
            "grand_totals": grand_totals
        }

    def add_title(self, sheet, formats, obj):
        # Keep company name and address fixed
        last_column_letter = chr(65 + len(COLUMNS) - 1)
        sheet.merge_range(f"C2:{last_column_letter}2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751",formats["company_name"],)
        
        # Keep image insertion as is
        sheet.insert_image("A1",get_module_resource("ccv_bao_cao", "static/src/img", "logo.png"),{"x_offset": 0, "y_offset": 0, "x_scale": 0.22, "y_scale": 0.22},)

        # Adjust main title to span all columns
        title_text = TITLE.upper()
        sheet.merge_range(f"A4:{last_column_letter}4", title_text, formats["title_main"])
        sheet.set_row(3, 35)
        
        # Add subtitle with date range and filters
        date_start = obj.date_from.strftime("%d/%m/%Y")
        date_end = obj.date_to.strftime("%d/%m/%Y")
        account = obj.account_id.code if obj.account_id else ""

        subtitle = f"Tài khoản: {account}; Loại tiền: VND; Từ ngày {date_start} đến ngày {date_end}"
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

        # Lặp qua từng nhân viên trong dữ liệu
        for partner_name, partner_data in lines_data.get("grouped", {}).items():
            # Ghi tiêu đề tên nhân viên
            sheet.merge_range(prod_row, 0, prod_row, len(COLUMNS) - 1,
                              f"NHÂN VIÊN: {partner_name.upper()}", formats["total_text_bold"])
            prod_row += 1

            # Ghi các dòng dữ liệu chi tiết cho nhân viên hiện tại
            current_partner_lines = partner_data.get("lines", [])
            for row in current_partner_lines:
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
            
            # Ghi dòng tổng cộng cho nhân viên hiện tại (Sub-Total)
            sums = partner_data.get("sums", {})
            
            # Nhãn "TỔNG CỘNG NHÂN VIÊN: [Tên nhân viên]"
            sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                              f"TỔNG CỘNG NHÂN VIÊN: {partner_name.upper()}", formats["total_text_bold"])
            
            # Ghi tổng của từng cột summable cho nhân viên hiện tại
            for col_idx, column_def in enumerate(COLUMNS):
                if column_def['sum']:
                    field_name = column_def.get('field')
                    sum_value = sums.get(field_name, 0)
                    
                    # Xác định định dạng tổng phù hợp
                    total_fmt_key = column_def['type'].replace('number', 'total')
                    # Dự phòng nếu định dạng 'total' cụ thể không tồn tại
                    fmt = formats.get(total_fmt_key, formats["total_int"]) 

                    sheet.write(prod_row, col_idx, sum_value, fmt)
                elif col_idx > merge_label_col_end_idx: # Điền ô trống cho các cột không summable sau nhãn
                    sheet.write(prod_row, col_idx, "", formats["text"])
            prod_row += 1 # Chuyển sang dòng tiếp theo
        
        # --- Phần Tổng Cộng Chung (Grand Total) ---
        grand_totals = lines_data.get("grand_totals", {})
        
        # Nhãn "TỔNG CỘNG TẤT CẢ NHÂN VIÊN"
        sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                          "TỔNG CỘNG TẤT CẢ NHÂN VIÊN", formats["total_text_bold"])
        
        # Ghi tổng của từng cột summable cho tất cả các nhân viên
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
            {"role": "Người lập", "signer": obj.voter_id.name_without_position if obj.voter_id and hasattr(obj.voter_id, 'name_without_position') else (obj.voter_id.name if obj.voter_id else "")},
            {"role": "Kế Toán Trưởng", "signer": obj.chief_acc_id.name_without_position if obj.chief_acc_id and hasattr(obj.chief_acc_id, 'name_without_position') else (obj.chief_acc_id.name if obj.chief_acc_id else "")},
            {"role": "Thủ trưởng đơn vị", "signer": obj.unit_heads_id.name_without_position if obj.unit_heads_id and hasattr(obj.unit_heads_id, 'name_without_position') else (obj.unit_heads_id.name if obj.unit_heads_id else "")},
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
        for obj in self.env['alpha.report'].browse(objects.ids):
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE,"author": self.env.user.name_without_position if hasattr(self.env.user, 'name_without_position') else self.env.user.name,})
            sheet.set_footer('&"Times New Roman"&11Trang &P/&N')
            sheet.set_landscape()
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)

