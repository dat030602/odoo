# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models
from odoo.modules.module import get_module_resource

import xlsxwriter
import ast
import json
import logging
import calendar
from collections import defaultdict

_logger = logging.getLogger(__name__)
TITLE = 'Báo cáo quỹ dự phòng'

COLUMNS = [
    {"size": 5,  "name": 'STT',                   'field': "no",                    "type": 'number_c_int',       "sum": False},
    {"size": 10, "name": 'Ngày',                  'field': "date",                  "type": 'date',               "sum": False},
    {"size": 20, "name": 'Tên Khách Hàng',        'field': "partner_name",          "type": 'text',               "sum": False},
    {"size": 15, "name": 'Số Đơn Hàng',           'field': "order_name",            "type": 'text',               "sum": False},
    {"size": 10, "name": 'Số Lượng (Tấn)',        'field': "quantity_ton",          "type": 'number_float3',      "sum": True},
    {"size": 10, "name": 'Đơn Giá Quỹ',           'field': "price_unit_bonus",      "type": 'number_int',         "sum": False},
    {"size": 10, "name": 'Thành Tiền',            'field': "amount_total",          "type": 'number_int',         "sum": True},
    {"size": 10, "name": 'Khu vực',               'field': "team_id",               "type": 'text',               "sum": False},
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


class RpBonusHistoryReport(models.AbstractModel):
    _name = "report.ccv_rp_bonus_history_report.rp_bonus_history_report"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE
    
    def _init_sum(self):
        """Khởi tạo dictionary để tính tổng dựa trên cấu hình COLUMNS."""
        return {col['field']: 0 for col in COLUMNS if col.get('sum')}

    def _get_data_export(self, obj):
        """
        Lấy và nhóm dữ liệu để xuất báo cáo theo team_id
        """
        
        # Lấy các team theo điều kiện
        team_ids = obj.team_ids if obj.team_ids else self.env['crm.team'].search([])
        
        date_start = f'{obj.date_from_year}-{obj.date_from_month.zfill(2)}-01 00:00:00'
        date_end = f'{obj.date_to_year}-{obj.date_to_month.zfill(2)}-{calendar.monthrange(int(obj.date_to_year), int(obj.date_to_month))[1]:02d} 23:59:59'
        
        # Dùng defaultdict để tự động tạo nhóm mới khi cần
        grouped_lines = defaultdict(list)
        
        for team_id in team_ids:
            # Lấy các bonus price unit của team này
            bonus_ids = self.env['sale.bonus.price.unit'].search([
                ('team_id', '=', team_id.id),
                ('date_from', '<=', date_end),
                '|',
                ('date_to', '>=', date_start),
                ('date_to', '=', False)
            ])
            
            for bonus_id in bonus_ids:
                pickings = self.env['stock.picking'].search([
                    ('date_done', '>=', date_start),
                    ('date_done', '<=', date_end),
                    ('state', '=', 'done'),
                    ('sale_id.bonus_price_id', '=', bonus_id.id)
                ])

                for picking in pickings:
                    # Tính tổng quantity và amount cho picking này
                    total_quantity = 0
                    total_amount = 0
                    price_unit_bonus = 0
                    
                    # Lấy tổng từ các move có quantity_done > 0 và có price_unit_bonus > 0
                    moves_with_bonus = picking.move_ids.filtered(
                        lambda m: m.quantity_done > 0 and m.sale_line_id and m.sale_line_id.price_unit_bonus > 0
                    )
                    
                    if moves_with_bonus:
                        total_quantity = sum(moves_with_bonus.mapped('quantity_done'))
                        # Lấy price_unit_bonus từ move đầu tiên (giả sử tất cả cùng giá)
                        price_unit_bonus = moves_with_bonus[0].sale_line_id.price_unit_bonus
                        total_amount = total_quantity * price_unit_bonus
                        
                        # Nhóm theo team_id với dữ liệu tổng của picking
                        grouped_lines[team_id].append({
                            'picking': picking,
                            'team_id': team_id,
                            'bonus_id': bonus_id,
                            'total_quantity': total_quantity,
                            'price_unit_bonus': price_unit_bonus,
                            'total_amount': total_amount
                        })

        # Chuẩn bị các biến tổng cuối cùng
        processed_data = {}
        grand_totals = self._init_sum()

        # Sắp xếp để các team có tên sắp xếp theo tên
        sorted_teams = sorted(grouped_lines.keys(), key=lambda k: k.name if k else '')

        for team_id in sorted_teams:
            lines_for_team = grouped_lines[team_id]
            
            # Bỏ qua nếu không có dòng nào
            if not lines_for_team:
                continue

            count = 0
            lines_data = []
            sums = self._init_sum()

            for line_data in lines_for_team:
                picking = line_data['picking']
                
                count += 1
                
                line_dict = {
                    "no": count,
                    'date': picking.stock_date_receipt,
                    'partner_name': picking.partner_id.name or '',
                    'order_name': picking.sale_id.name or '',
                    'quantity_ton': line_data['total_quantity'],
                    'price_unit_bonus': line_data['price_unit_bonus'],
                    'amount_total': line_data['total_amount'],
                    'team_id': team_id.code,
                }
                lines_data.append(line_dict)

                # Tính tổng một cách trực tiếp và an toàn
                for key in sums.keys():
                    sums[key] += line_dict.get(key, 0)

            # Cộng dồn vào tổng cuối cùng
            for key in grand_totals.keys():
                grand_totals[key] += sums.get(key, 0)

            # Lấy tên team để làm key cho dictionary cuối cùng
            group_name = team_id.report_name if team_id else "Không có đội bán hàng"
            processed_data[group_name] = {
                "lines": lines_data,
                "sums": sums
            }
        
        # Hàm replace_zeros để thay thế giá trị 0 bằng chuỗi rỗng
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
        
        replace_zeros(processed_data)
        replace_zeros(grand_totals)

        return {
            "grouped": processed_data,
            "grand_totals": grand_totals
        }

    def add_title(self, sheet, formats, obj):
        # Keep company name and address fixed
        sheet.merge_range("C2:G2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751",formats["company_name"],)
        sheet.merge_range("C3:G3", "23 Lô B, Đường số 1, P. Phú Thuận, Q.7", formats["company_name"])
        
        # Keep image insertion as is
        sheet.insert_image("A1",get_module_resource("ccv_bao_cao", "static/src/img", "logo.png"),{"x_offset": 0, "y_offset": 0, "x_scale": 0.22, "y_scale": 0.22},)

        # Calculate the last column letter dynamically
        last_column_letter = chr(65 + len(COLUMNS) - 1)

        # Adjust main title to span all columns
        title_text = TITLE.upper()
        sheet.merge_range(f"A4:{last_column_letter}4", title_text, formats["title_main"])
        sheet.set_row(3, 35)
        title_text = 'Khu vực: ' + (', '.join(obj.team_ids.mapped('report_name')) if len(obj.team_ids) > 0 and len(obj.team_ids) <= 3 else 'Tất cả đội bán hàng')
        sheet.merge_range(f"A5:{last_column_letter}5", title_text, formats["title_sub"])
        sheet.set_row(4, 25)
        title_text = 'Từ tháng ' + obj.date_from_month + '/' + obj.date_from_year + ' đến tháng ' + obj.date_to_month + '/' + obj.date_to_year
        sheet.merge_range(f"A6:{last_column_letter}6", title_text, formats["title_sub"])
        sheet.set_row(4, 25)

    def add_header(self, sheet, formats, obj):
        row = 7
        
        for col_idx, column_def in enumerate(COLUMNS):
            sheet.set_column(col_idx, col_idx, column_def.get('size', 10))
            sheet.write(row, col_idx, column_def.get('name', ''), formats["header"])

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

        # Lặp qua từng đội bán hàng trong dữ liệu
        for team_name, team_data in lines_data.get("grouped", {}).items():
            # Ghi tiêu đề tên đội bán hàng
            sheet.merge_range(prod_row, 0, prod_row, len(COLUMNS) - 1,
                              f"{team_name.upper()}", formats["total_text_bold"])
            prod_row += 1

            # Ghi các dòng dữ liệu chi tiết cho đội bán hàng hiện tại
            current_team_lines = team_data.get("lines", [])
            for row in current_team_lines:
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
            
            # Ghi dòng tổng cộng cho đội bán hàng hiện tại (Sub-Total)
            sums = team_data.get("sums", {})
            
            # Nhãn "TỔNG CỘNG ĐỘI BÁN HÀNG: [Tên đội]"
            sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                              f"TỔNG CỘNG: {team_name.upper()}", formats["total_text_bold"])
            
            # Ghi tổng của từng cột summable cho đội bán hàng hiện tại
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
        
        # Nhãn "TỔNG CỘNG TẤT CẢ ĐỘI BÁN HÀNG"
        sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                          "TỔNG CỘNG TẤT CẢ ĐỘI BÁN HÀNG", formats["total_text_bold"])
        
        # Ghi tổng của từng cột summable cho tất cả các đội bán hàng
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

        date_merge_end_col_idx = last_column_index

        date_merge_end_col_letter = chr(65 + date_merge_end_col_idx)

        sheet.merge_range(f"A{row}:{date_merge_end_col_letter}{row}", "Đồng Nai, Ngày ........ tháng ........ năm ............", formats["signature_date"])

        row += 1 

        signature_blocks = [
            {"role": "Người Lập", "signer": obj.voter_id.name_without_position or obj.voter_id.name if obj.voter_id else ""},
            {"role": "Thủ trưởng đơn vị", "signer": obj.director_id.name_without_position or obj.director_id.name if obj.director_id else ""},
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
        self = self.sudo()
        for obj in objects:
            obj = obj.sudo()
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE,"author": self.env.user.name_without_position,})
            # sheet.set_landscape()
            sheet.set_portrait()
            sheet.set_paper(9)
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)
