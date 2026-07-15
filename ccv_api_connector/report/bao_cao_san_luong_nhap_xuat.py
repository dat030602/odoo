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
TITLE = 'Báo cáo sản lượng nhập xuất'


COLUMNS = [
    {"size":  5,  "name": 'STT'                  , 'field':"no"                  , "type": 'number_c_int'       , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 13,  "name": 'Ngày'                 , 'field':"date"                , "type": 'date'               , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 12,  "name": 'Loại'                 , 'field':"type"                , "type": 'text'               , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 25,  "name": 'Đại lý/NCC'           , 'field':"partner_name"        , "type": 'text'               , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 15,  "name": 'Đơn hàng'             , 'field':"order"               , "type": 'text'               , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 15,  "name": 'Số xe'                , 'field':"vehicle_num"         , "type": 'text'               , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 15,  "name": 'Tài xế'               , 'field':"vehicle_driver"      , "type": 'text'               , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 10,  "name": 'ĐVT'                  , 'field':"uom_id"              , "type": 'text'               , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 10,  "name": 'Số lượng phiếu kho'   , 'field':"quantity"            , "type": 'number_float3'      , "sum": True, "color": "black", "bg_color": "white" },
    {"size": 10,  "name": 'Cửa nhập/xuất'        , 'field':"gate"                , "type": 'number_c_int'       , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 10,  "name": 'Bốc xếp'              , 'field':"loading"             , "type": 'text'               , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 10,  "name": 'Thủ kho'              , 'field':"stocker"             , "type": 'text'               , "sum": False, "color": "black", "bg_color": "white" },
    {"size": 10,  "name": 'Ghi chú'              , 'field':"note"                , "type": 'text'               , "sum": False, "color": "black", "bg_color": "white" },
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


class bao_cao_san_luong_nhap_xuat(models.AbstractModel):
    _name = "report.ccv_api_connector.bao_cao_san_luong_nhap_xuat"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE

    @staticmethod
    def html_to_text(html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()

    def _get_data_export(self, obj):
        # obj = self.env['rp.production.report.wizard']
        count = 0
        lines = []
        grand_totals = {}
        for col_idx, column_def in enumerate(COLUMNS):
            if column_def.get('sum',False):
                grand_totals.update({column_def.get('field',''):0})
        # Khi tick vao xe rot, lay xe co is_next_day = True
        if obj.is_next_day_fall_vehicle:
            domain = [('is_next_day','=',True)]
        else:
            domain = [('name','!=',False)]

        if obj.date:
            domain.append(('sale_vehicle_id.date', '>=', obj.date))
        if obj.date_to:
            domain.append(('sale_vehicle_id.date', '<=', obj.date_to))
        if obj.type:
            domain.append(('type', '=', obj.type))
        line_ids = self.env['sale.vehicle.in.out.line'].search(domain).sorted(lambda l: (1 if (l.note and 'Xe rớt' in l.note) else 0, l.loading_id.name or ""))
        
        is_department_id = False
        if obj.department_id:
            line_ids = line_ids.filtered(lambda l: l.loading_id == obj.department_id or l.loading2_id == obj.department_id)
            is_department_id = True

        for line_id in line_ids:
            count += 1
            order = line_id.sale_order_ids.mapped('name') if line_id.sale_order_ids and line_id.type == 'out' else line_id.purchase_order_ids.mapped('name')

            is_loading2_id = False
            is_loading1_id = False
            if obj.department_id:
                is_loading2_id = line_id.loading2_id == obj.department_id
                is_loading1_id = line_id.loading_id == obj.department_id

            has_loading1 = bool((line_id.loading and str(line_id.loading) != 'False') or line_id.loading_id)
            has_loading2 = bool((line_id.loading2 and str(line_id.loading2) != 'False') or line_id.loading2_id)
            divide_qty = has_loading1 and has_loading2

            if (not is_department_id) or is_loading1_id:
                val = {
                    "no": count,
                    'date': line_id.sale_vehicle_id.date if line_id.sale_vehicle_id else False,
                    'type': "Xuất" if line_id.type == 'out' else "Nhập",
                    'partner_name': line_id.partner_name if line_id.partner_name else '',
                    'order': ','.join(order) if order else '',
                    'vehicle_num': line_id.vehicle_num if line_id.vehicle_num else '',
                    'vehicle_driver': line_id.vehicle_driver if line_id.vehicle_driver and line_id.vehicle_driver != 'False' else '',
                    'uom_id': line_id.uom_id.name if line_id.uom_id else '',
                    'quantity': line_id.quantity / 2 if divide_qty else line_id.quantity,
                    'gate': line_id.gate if line_id.gate else '',
                    'loading': line_id.loading_id.name if line_id.loading_id else (line_id.loading if line_id.loading else ''),
                    'stocker': line_id.stocker_id.name_without_position if line_id.stocker_id else (line_id.stocker if line_id.stocker else ''),
                    'note': line_id.user_note if obj.is_next_day_fall_vehicle else (line_id.note if line_id.note else ''),
                }
                lines.append(val)

            if has_loading2 and ((not is_department_id) or is_loading2_id):
                val2 = {
                    "no": count,
                    'date': line_id.sale_vehicle_id.date if line_id.sale_vehicle_id else False,
                    'type': "Xuất" if line_id.type == 'out' else "Nhập",
                    'partner_name': line_id.partner_name if line_id.partner_name else '',
                    'order': ','.join(order) if order else '',
                    'vehicle_num': line_id.vehicle_num if line_id.vehicle_num else '',
                    'vehicle_driver': line_id.vehicle_driver if line_id.vehicle_driver and line_id.vehicle_driver != 'False' else '',
                    'uom_id': line_id.uom_id.name if line_id.uom_id else '',
                    'quantity': line_id.quantity / 2 if divide_qty else line_id.quantity,
                    'gate': line_id.gate if line_id.gate else '',
                    'loading': line_id.loading2_id.name if line_id.loading2_id else (line_id.loading2 if line_id.loading2 else ''),
                    'stocker': line_id.stocker_id.name_without_position if line_id.stocker_id else (line_id.stocker if line_id.stocker else ''),
                    'note': line_id.user_note if obj.is_next_day_fall_vehicle else (line_id.note if line_id.note else ''),
                }
                lines.append(val2)

            if lines:
                for col_idx, column_def in enumerate(COLUMNS):
                    if column_def.get('sum',False):
                        sums = sum([line.get(column_def.get('field',''), 0) for line in lines])
                        grand_totals.update({column_def.get('field',''): sums})
        return {
            "all_lines": lines,
            "grand_totals": grand_totals
        }
    
    def add_title(self, sheet, formats, obj):
        # obj = self.env['rp.production.report.wizard']
        # Keep company name and address fixed
        sheet.merge_range("C2:G2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751",formats["company_name"],)
        sheet.merge_range("C3:G3", "23 Lô B, Đường số 1, P. Phú Thuận, Q.7", formats["company_name"])
        
        # Keep image insertion as is
        sheet.insert_image("A1",get_module_resource("ccv_bao_cao", "static/src/img", "logo.png"),{"x_offset": 0, "y_offset": 0, "x_scale": 0.22, "y_scale": 0.22},)

        # Calculate the last column letter dynamically
        last_column_letter = chr(65 + len(COLUMNS) - 1)
        
        row = 6

        # Adjust main title to span all columns
        title_text = TITLE.upper()
        sheet.merge_range(f"A{row - 1}:{last_column_letter}{row - 1}", title_text, formats["title_main"])
        sheet.set_row(row - 2, 35)
        
        row += 1
        title_text = "Phòng ban: %s" % (obj.department_id.name if obj.department_id else "Tất cả")
        sheet.merge_range(f"A{row - 1}:{last_column_letter}{row - 1}", title_text, formats["title_sub"])
        sheet.set_row(row - 2, 20)
        
        row += 1
        if obj.date and obj.date_to and obj.date != obj.date_to:
            title_text = "Từ ngày %s đến ngày %s" % (obj.date.strftime("%d/%m/%Y"), obj.date_to.strftime("%d/%m/%Y"))
        elif obj.date:
            title_text = "Ngày %s" % obj.date.strftime("%d/%m/%Y")
        else:
            title_text = ""
        sheet.merge_range(f"A{row - 1}:{last_column_letter}{row - 1}", title_text, formats["title_sub"])
        sheet.set_row(row - 2, 20)

    def add_header(self, sheet, formats, obj):
        w_row_header = 8
        for i, header in enumerate(COLUMNS):
            sheet.write(w_row_header, i, header.get("name", ""), formats["header"])

    def add_body(self, sheet, formats, obj):
        lines_data = self._get_data_export(obj)
        prod_row = 9

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

        # Ghi các dòng dữ liệu chi tiết (không nhóm theo kho)
        all_lines = lines_data.get("all_lines", []) # Assuming 'all_lines' now holds all data
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
        
        # Nhãn "TỔNG CỘNG TẤT CẢ KHO"
        sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                        "TỔNG CỘNG", formats["total_text_bold"]) # Changed label to "TỔNG CỘNG"
        
        # Ghi tổng của từng cột summable
        for col_idx, column_def in enumerate(COLUMNS):
            if column_def['sum']:
                field_name = column_def.get('field')
                sum_value = grand_totals.get(field_name, 0)
                
                # Xác định định dạng tổng phù hợp
                total_fmt_key = column_def['type'].replace('number', 'total')
                fmt = formats.get(total_fmt_key, formats["total_int"]) 

                sheet.write(prod_row, col_idx, sum_value, fmt)
            elif col_idx > merge_label_col_end_idx: # Điền ô trống cho các cột không summable sau nhãn
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
            {"role": obj.sudo()._fields['voter_id'].string, "signer": obj.voter_id.name_without_position if obj.voter_id else ""},
            {"role": obj.sudo()._fields['loading_id'].string, "signer": obj.loading_id.name_without_position if obj.loading_id else ""},
            {"role": obj.sudo()._fields['stocker_id'].string, "signer": obj.stocker_id.name_without_position if obj.stocker_id else ""},
            {"role": obj.sudo()._fields['hr_admin_department_id'].string, "signer": obj.hr_admin_department_id.name_without_position if obj.hr_admin_department_id else ""},
            {"role": obj.sudo()._fields['chief_finance_id'].string, "signer": obj.chief_finance_id.name_without_position if obj.chief_finance_id else ""},
            {"role": obj.sudo()._fields['director_id'].string, "signer": obj.director_id.name_without_position if obj.director_id else ""},
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

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, data_raw, objects):
        for obj in objects:
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE, "author": self.env.user.name_without_position,})
            
            sheet.set_landscape() 
            # Đặt khổ giấy A4 (Paper size 9 for A4)
            sheet.set_paper(9)
            sheet.set_margins(
                left=0.18,
                right=0.23,
                top=0.32,
                bottom=0.34
            )
            sheet.set_header(margin=0.3)
            sheet.set_footer(margin=0.3)
            sheet.center_horizontally()
            sheet.fit_to_pages(1, 0)

            # sheet.set_zoom(79) 
            # sheet.set_margins(0.26,0.26,0.26,0.26)

            # --- End Cài đặt bản in và lề ---

            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)


# COLUMNS mapping for rp.san.luong.nhap.xuat (uses uom_name instead of uom_id)
COLUMNS_RP = [
    {"size":  5,  "name": 'STT'                , 'field': "no"           , "type": 'number_c_int' , "sum": False},
    {"size": 13,  "name": 'Ngày'               , 'field': "date"         , "type": 'date'         , "sum": False},
    {"size": 12,  "name": 'Loại'               , 'field': "type"         , "type": 'text'         , "sum": False},
    {"size": 25,  "name": 'Đại lý/NCC'         , 'field': "partner_name" , "type": 'text'         , "sum": False},
    {"size": 15,  "name": 'Đơn hàng'           , 'field': "order"        , "type": 'text'         , "sum": False},
    {"size": 15,  "name": 'Số xe'              , 'field': "vehicle_num"  , "type": 'text'         , "sum": False},
    {"size": 15,  "name": 'Tài xế'             , 'field': "vehicle_driver", "type": 'text'        , "sum": False},
    {"size": 10,  "name": 'ĐVT'               , 'field': "uom_name"     , "type": 'text'         , "sum": False},
    {"size": 10,  "name": 'Số lượng phiếu kho' , 'field': "quantity"     , "type": 'number_float3', "sum": True },
    {"size": 10,  "name": 'Cửa nhập/xuất'      , 'field': "gate"         , "type": 'text'         , "sum": False},
    {"size": 10,  "name": 'Bốc xếp'            , 'field': "loading"      , "type": 'text'         , "sum": False},
    {"size": 10,  "name": 'Thủ kho'            , 'field': "stocker"      , "type": 'text'         , "sum": False},
    {"size": 10,  "name": 'Ghi chú'            , 'field': "note"         , "type": 'text'         , "sum": False},
]


class rp_san_luong_nhap_xuat_report(models.AbstractModel):
    _name = "report.ccv_api_connector.rp_san_luong_nhap_xuat_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE

    def _get_data_export(self, obj):
        lines = []
        grand_totals = {col['field']: 0 for col in COLUMNS_RP if col.get('sum')}
        for line in obj.line_ids.sorted('no'):
            val = {
                'no': line.no,
                'date': line.date,
                'type': line.type or '',
                'partner_name': line.partner_name or '',
                'order': line.order or '',
                'vehicle_num': line.vehicle_num or '',
                'vehicle_driver': line.vehicle_driver or '',
                'uom_name': line.uom_name or '',
                'quantity': line.quantity,
                'gate': line.gate or '',
                'loading': line.loading or '',
                'stocker': line.stocker or '',
                'note': line.note or '',
            }
            lines.append(val)
            for col in COLUMNS_RP:
                if col.get('sum'):
                    grand_totals[col['field']] = grand_totals.get(col['field'], 0) + (val.get(col['field']) or 0)
        return {'all_lines': lines, 'grand_totals': grand_totals}

    def add_title(self, sheet, formats, obj):
        sheet.merge_range("C2:G2", "Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751", formats["company_name"])
        sheet.merge_range("C3:G3", "23 Lô B, Đường số 1, P. Phú Thuận, Q.7", formats["company_name"])
        sheet.insert_image("A1", get_module_resource("ccv_bao_cao", "static/src/img", "logo.png"),
                           {"x_offset": 0, "y_offset": 0, "x_scale": 0.22, "y_scale": 0.22})

        last_column_letter = chr(65 + len(COLUMNS_RP) - 1)
        row = 6
        sheet.merge_range(f"A{row - 1}:{last_column_letter}{row - 1}", TITLE.upper(), formats["title_main"])
        sheet.set_row(row - 2, 35)

        row += 1
        title_text = "Phòng ban: %s" % (obj.department_id.name if obj.department_id else "Tất cả")
        sheet.merge_range(f"A{row - 1}:{last_column_letter}{row - 1}", title_text, formats["title_sub"])
        sheet.set_row(row - 2, 20)

        row += 1
        if obj.date and obj.date_to and obj.date != obj.date_to:
            title_text = "Từ ngày %s đến ngày %s" % (obj.date.strftime("%d/%m/%Y"), obj.date_to.strftime("%d/%m/%Y"))
        elif obj.date:
            title_text = "Ngày %s" % obj.date.strftime("%d/%m/%Y")
        else:
            title_text = ""
        sheet.merge_range(f"A{row - 1}:{last_column_letter}{row - 1}", title_text, formats["title_sub"])
        sheet.set_row(row - 2, 20)

    def add_header(self, sheet, formats, obj):
        for i, header in enumerate(COLUMNS_RP):
            sheet.write(8, i, header.get("name", ""), formats["header"])

    def add_body(self, sheet, formats, obj):
        lines_data = self._get_data_export(obj)
        prod_row = 9
        first_sum_idx = next((i for i, c in enumerate(COLUMNS_RP) if c['sum']), len(COLUMNS_RP) - 1)
        merge_label_end = max(0, first_sum_idx - 1)

        for row in lines_data.get("all_lines", []):
            for col_idx, col_def in enumerate(COLUMNS_RP):
                sheet.set_column(col_idx, col_idx, col_def.get('size', 10))
                fmt = formats[col_def.get('type', 'text')]
                cell_value = row.get(col_def.get('field'))
                if col_def.get('type') == 'date' and isinstance(cell_value, datetime):
                    cell_value = cell_value.date()
                sheet.write(prod_row, col_idx, cell_value, fmt)
            prod_row += 1

        grand_totals = lines_data.get("grand_totals", {})
        sheet.merge_range(prod_row, 0, prod_row, merge_label_end, "TỔNG CỘNG", formats["total_text_bold"])
        for col_idx, col_def in enumerate(COLUMNS_RP):
            if col_def['sum']:
                total_fmt_key = col_def['type'].replace('number', 'total')
                fmt = formats.get(total_fmt_key, formats["total_int"])
                sheet.write(prod_row, col_idx, grand_totals.get(col_def['field'], 0), fmt)
            elif col_idx > merge_label_end:
                sheet.write(prod_row, col_idx, "", formats["text"])
        prod_row += 1

    def add_signatures(self, sheet, formats, obj):
        row = sheet.dim_rowmax + 3
        last_col = len(COLUMNS_RP) - 1
        total_cols = len(COLUMNS_RP)

        date_start = max(0, last_col - 2)
        sheet.merge_range(
            f"{chr(65 + date_start)}{row}:{chr(65 + last_col)}{row}",
            "Ngày ..... tháng ..... năm .........", formats["signature_date"])
        row += 1

        signature_blocks = [
            {"role": obj.sudo()._fields['voter_id'].string,
             "signer": obj.voter_id.name_without_position if obj.voter_id else ""},
            {"role": obj.sudo()._fields['loading_id'].string,
             "signer": obj.loading_id.name_without_position if obj.loading_id else ""},
            {"role": obj.sudo()._fields['stocker_id'].string,
             "signer": obj.stocker_id.name_without_position if obj.stocker_id else ""},
            {"role": obj.sudo()._fields['hr_admin_department_id'].string,
             "signer": obj.hr_admin_department_id.name_without_position if obj.hr_admin_department_id else ""},
            {"role": obj.sudo()._fields['chief_finance_id'].string,
             "signer": obj.chief_finance_id.name_without_position if obj.chief_finance_id else ""},
            {"role": obj.sudo()._fields['director_id'].string,
             "signer": obj.director_id.name_without_position if obj.director_id else ""},
        ]
        n = len(signature_blocks)
        block_w = max(1, total_cols // n)
        cur = 0
        for i, block in enumerate(signature_blocks):
            s = cur
            e = last_col if i == n - 1 else s + block_w - 1
            sheet.merge_range(f"{chr(65+s)}{row}:{chr(65+e)}{row}", block["role"], formats["signature_name"])
            cur = e + 1
        row += 5
        cur = 0
        for i, block in enumerate(signature_blocks):
            s = cur
            e = last_col if i == n - 1 else s + block_w - 1
            sheet.merge_range(f"{chr(65+s)}{row}:{chr(65+e)}{row}", block["signer"], formats["signature_name"])
            cur = e + 1

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, data_raw, objects):
        for obj in objects:
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE, "author": self.env.user.name_without_position})
            sheet.set_landscape()
            sheet.set_paper(9)
            sheet.set_margins(left=0.18, right=0.23, top=0.32, bottom=0.34)
            sheet.set_header(margin=0.3)
            sheet.set_footer(margin=0.3)
            sheet.center_horizontally()
            sheet.fit_to_pages(1, 0)
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)
