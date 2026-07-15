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

_logger = logging.getLogger(__name__)
TITLE = 'BÁO CÁO SẢN LƯỢNG'


COLUMNS = [
    {"size":  5,  "name": 'STT'                , 'field':"no"                 , "type": 'number_c_int'       , "sum": False  },
    {"size": 12,  "name": 'Ngày dùng tồn'      , 'field':"stock_date_receipt" , "type": 'text_c'             , "sum": False  },
    {"size": 20,  "name": 'Mã tham chiếu'      , 'field':"name"               , "type": 'date'               , "sum": False  },
    {"size": 20,  "name": 'Mã sản phẩm'        , 'field':"product_code"       , "type": 'text_c'             , "sum": False  },
    {"size": 25,  "name": 'Tên sản phẩm'       , 'field':"product_name"       , "type": 'text'               , "sum": False  },
    {"size": 15,  "name": 'ĐVT'                , 'field':"uom_name"           , "type": 'text_c'             , "sum": False  },
    {"size": 10,  "name": 'Số lượng sản xuất'  , 'field':"quantity"           , "type": 'number_c_float3'    , "sum": True   },
    {"size": 12,  "name": 'Người phụ trách'    , 'field':"user_id"            , "type": 'text_c'             , "sum": False  },
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
        "text_c": format_workbook(workbook, 11.5, border=1, align='center', text_wrap=True),
        "text": format_workbook(workbook, 11.5, border=1, align='left', text_wrap=True),
        "date": format_workbook(workbook, 11.5, border=1, num_format='dd/mm/yyyy', align='center', text_wrap=True),
        "datetime": format_workbook(workbook, 11.5, border=1, num_format='dd/mm/yyyy hh:mm:ss', align='center', text_wrap=True),

        "datetime": format_workbook(workbook, 11.5, border=1, num_format='dd/mm/yyyy hh:mm:ss', align='center', text_wrap=True),


        # Numbers
        "number_int": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0"),
        "number_float2": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0.00"),
        "number_float3": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0.000"),
        "number_c_int": format_workbook(workbook, 10, border=1, align='center', num_format="#,##0"),
        "number_c_float2": format_workbook(workbook, 10, border=1, align='center', num_format="#,##0.00"),
        "number_c_float3": format_workbook(workbook, 10, border=1, align='center', num_format="#,##0.000"),
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


class RpProductionReportXlsxReport(models.AbstractModel):
    _name = "report.ccv_bao_cao.rp_production_report_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE

    def _get_data_export(self, obj):
        # obj = self.env['rp.production.report.wizard']
        start_datetime = fields.Datetime.to_datetime(obj.date_from)
        end_datetime = fields.Datetime.end_of(fields.Datetime.to_datetime(obj.date_to), 'day')
        count = 0
        lines = []
        grand_totals = {}
        for col_idx, column_def in enumerate(COLUMNS):
            if column_def.get('sum',False):
                grand_totals.update({column_def.get('field',''):0})
        picking_type_ids = obj.picking_type_ids if obj.picking_type_ids else self.env['stock.picking.type'].search([])
        for picking_type_id in picking_type_ids:
            mrp_env = self.env['mrp.production']
            mrps = mrp_env.search([
                ('stock_date_receipt', '>=', start_datetime),
                ('stock_date_receipt', '<=', end_datetime),
                ('picking_type_id', '=', picking_type_id.id),
                ('state', '=', 'done'),
            ]).sorted('stock_date_receipt')

            for mrp in mrps:
                count += 1
                val = {
                    "no": count,
                    "stock_date_receipt": mrp.stock_date_receipt.strftime("%d/%m/%Y"),
                    "name": mrp.name,
                    "user_id": mrp.user_id.name_without_position if mrp.user_id else "",
                    "product_code": mrp.product_id.default_code if mrp.product_id.default_code else "",
                    "product_name": mrp.product_id.name,
                    "uom_name": mrp.product_uom_id.name,
                    "quantity": mrp.qty_produced,
                }
                lines.append(val)

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

        # Adjust main title to span all columns
        picking_type_ids = obj.picking_type_ids.mapped("factory_name")
        if len(picking_type_ids) == 1:
            factory_name = " Nhà máy " + picking_type_ids[0]
        elif len(picking_type_ids) > 1:
            factory_name = "Nhà máy: " + ",".join(picking_type_ids)
        else:
            factory_name = "Nhà máy: Tất cả"

        title_text = TITLE.upper()
        if len(picking_type_ids) == 1:
            title_text += factory_name.upper()
        sheet.merge_range(f"A4:{last_column_letter}4", title_text, formats["title_main"])
        sheet.set_row(3, 35)
        
        # Adjust subtitle to span all columns
        if obj.date_from == obj.date_to:
            title_text = "Ngày %s tháng %s năm %s" % (obj.date_from.day,obj.date_from.month,obj.date_from.year)
        else:
            title_text = "Từ ngày %s đến ngày %s" % (obj.date_from.strftime("%d/%m/%Y"),obj.date_to.strftime("%d/%m/%Y"),)
        if len(picking_type_ids) != 1:
            title_text = '%s; %s' % (factory_name, title_text)
        sheet.merge_range(f"A5:{last_column_letter}5", title_text, formats["title_sub"])
        sheet.set_row(4, 20)

    def add_header(self, sheet, formats, obj):
        w_row_header = 6
        for i, header in enumerate(COLUMNS):
            sheet.write(w_row_header, i, header.get("name", ""), formats["header"])

    def add_body(self, sheet, formats, obj):
        lines_data = self._get_data_export(obj)
        prod_row = 7

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
        # This will be the row where the date "Đồng Nai, Ngày..." is placed.
        # Let's assume sheet.dim_rowmax + 3 results in row 41 based on your image.
        date_row = sheet.dim_rowmax + 3

        last_column_index = len(COLUMNS) - 1
        total_columns = len(COLUMNS) 

        # --- Date Signature ---
        date_merge_start_col_idx = max(0, last_column_index - 2)
        date_merge_end_col_idx = last_column_index

        date_merge_start_col_letter = chr(65 + date_merge_start_col_idx)
        date_merge_end_col_letter = chr(65 + date_merge_end_col_idx)

        sheet.merge_range(f"{date_merge_start_col_letter}{date_row}:{date_merge_end_col_letter}{date_row}", "Đồng Nai, Ngày ..... tháng ..... năm .........", formats["signature_date"])

        # --- Signature Blocks Definition ---
        signature_blocks = [
            {"role": "Người Lập", "signer": obj.voter_id.name_without_position if obj.voter_id else ""},
            {"role": "Tổ trưởng nhà máy", "signer": obj.factory_team_leader_id.name_without_position if obj.factory_team_leader_id else ""},
            {"role": "Thủ kho thành phẩm", "signer": obj.finished_goods_warehouse_keeper_id.name_without_position if obj.finished_goods_warehouse_keeper_id else ""},
            {"role": "Phòng HCNS", "signer": obj.hr_admin_department_id.name_without_position if obj.hr_admin_department_id else ""},
            {"role": "Phòng Kế toán", "signer": obj.chief_finance_id.name_without_position if obj.chief_finance_id else ""},
            {"role": "Thủ trưởng đơn vị", "signer": obj.director_id.name_without_position if obj.director_id else ""},
        ]

        num_signature_blocks = len(signature_blocks)
        
        # Base block width for middle blocks, ensure at least 1
        # This 'block_width' will now primarily apply to the middle sections.
        # The first and last blocks will have their width explicitly set to 2.
        # We need to account for the 2 columns taken by the first and last blocks.
        remaining_columns = total_columns - 2 * 2 # total_columns - (width of first block) - (width of last block)
        remaining_blocks = num_signature_blocks - 2 # num_blocks - first - last

        # Calculate block_width for the *middle* sections. Ensure it's at least 1.
        # If there are no middle blocks (e.g., only 1 or 2 total blocks), this might be 0 or less.
        # Handle this by making it 1.
        if remaining_blocks > 0:
            middle_block_width = max(1, remaining_columns // remaining_blocks)
        else:
            middle_block_width = 1 # If only 1 or 2 blocks, middle blocks don't exist in this sense.
        
        _logger.info(f"Calculated middle_block_width: {middle_block_width}")

        # --- Write Signature Roles ---
        # Row for "Thủ trưởng đơn vị" role
        thu_truong_dv_role_row = date_row + 1
        # Row for "Người Lập", "Tổ trưởng nhà máy", etc. roles
        other_roles_row = date_row

        current_col_idx = 0
        for i, block in enumerate(signature_blocks):
            col_start_idx = current_col_idx
            
            # Determine the correct row for the current role
            if i == num_signature_blocks - 1: # This is the "Thủ trưởng đơn vị" block (last block)
                target_row = thu_truong_dv_role_row
                col_end_idx = last_column_index # Its role is at the very end
                col_start_idx = max(0, last_column_index - 1) # Start 2 columns from the end
            elif i == 0: # This is the "Người Lập" block (first block)
                target_row = other_roles_row + 1
                col_end_idx = col_start_idx + 2 - 1
            else: # All other roles (middle blocks)
                target_row = other_roles_row
                col_end_idx = col_start_idx + middle_block_width - 1
                col_end_idx = min(col_end_idx, last_column_index) # Ensure within bounds

            # Use sheet.write for single cells, merge_range for multiple
            if col_start_idx == col_end_idx:
                sheet.write(target_row, col_start_idx, block["role"], formats["signature_name"])
            else:
                col_from_letter = chr(65 + col_start_idx)
                col_to_letter = chr(65 + col_end_idx)
                sheet.merge_range(f"{col_from_letter}{target_row}:{col_to_letter}{target_row}", block["role"], formats["signature_name"])

            # Update current_col_idx based on the actual width used
            current_col_idx = col_end_idx + 1
                
        # --- Write Signer Names ---
        # Row for "Hoàng Mai Đức" (Thủ trưởng đơn vị signer)
        thu_truong_dv_signer_row = date_row + 6
        # Row for "Nguyễn Văn Đạt", etc. signers
        other_signers_row = date_row + 5

        current_col_idx = 0
        for i, block in enumerate(signature_blocks):
            col_start_idx = current_col_idx
            
            # Determine the correct row for the current signer
            if i == num_signature_blocks - 1: # This is the "Thủ trưởng đơn vị" signer block (last block)
                target_row = thu_truong_dv_signer_row
                col_end_idx = last_column_index # Its name is at the very end
                col_start_idx = max(0, last_column_index - 1) # Start 2 columns from the end
            elif i == 0: # This is the "Người Lập" signer block (first block)
                target_row = other_signers_row + 1
                col_end_idx = col_start_idx + 2 - 1
            else: # All other signers (middle blocks)
                target_row = other_signers_row
                col_end_idx = col_start_idx + middle_block_width - 1
                col_end_idx = min(col_end_idx, last_column_index) # Ensure within bounds

            # Use sheet.write for single cells, merge_range for multiple
            if col_start_idx == col_end_idx:
                sheet.write(target_row, col_start_idx, block["signer"], formats["signature_name"])
            else:
                col_from_letter = chr(65 + col_start_idx)
                col_to_letter = chr(65 + col_end_idx)
                sheet.merge_range(f"{col_from_letter}{target_row}:{col_to_letter}{target_row}", block["signer"], formats["signature_name"])

            # Update current_col_idx based on the actual width used
            current_col_idx = col_end_idx + 1

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, obj, objects):
        for obj in objects:
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE, "author": self.env.user.name_without_position,})
            
            # sheet.set_landscape() 
            # Đặt khổ giấy A4 (Paper size 9 for A4)
            sheet.set_paper(9)

            sheet.set_zoom(79) 
            sheet.set_margins(0.26,0.26,0.26,0.26)

            # --- End Cài đặt bản in và lề ---

            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)

