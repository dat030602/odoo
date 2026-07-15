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
TITLE = 'Bảng Tổng hợp Xuất - Nhập - Tồn kho Hàng hóa'

# Định nghĩa các cột cho báo cáo
COLUMNS = [
    {"size": 5,  "name": 'STT', 'field': "no", "type": 'number_c_int', "sum": False},
    {"size": 15, "name": 'Nhóm', 'field': "stock_valuation_account_id", "type": 'text', "sum": False},
    {"size": 15, "name": 'Mã sản phẩm', 'field': "product_code", "type": 'text', "sum": False},
    {"size": 30, "name": 'Tên sản phẩm', 'field': "product_id", "type": 'text', "sum": False},
    {"size": 10, "name": 'Đơn vị tính', 'field': "uom_id", "type": 'text', "sum": False},

    # Ton dau ky
    {"size": 8, "group": "Tồn đầu kỳ", "name": 'Số lượng', 'field': "qty_begin", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Tồn đầu kỳ", "name": 'Giá trị', 'field': "value_begin", "type": 'number_int', "sum": True},

    # Nhap mua
    {"size": 8, "group": "Nhập mua", "name": 'Số lượng', 'field': "qty_import_purchase", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Nhập mua", "name": 'Giá trị', 'field': "value_import_purchase", "type": 'number_int', "sum": True},

    # Nhap san xuat
    {"size": 8, "group": "Nhập sản xuất", "name": 'Số lượng', 'field': "qty_import_production", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Nhập sản xuất", "name": 'Giá trị', 'field': "value_import_production", "type": 'number_int', "sum": True},

    # Nhap thua kiem ke
    {"size": 8, "group": "Nhập thừa kiểm kê", "name": 'Số lượng', 'field': "qty_import_inventory_adjustment", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Nhập thừa kiểm kê", "name": 'Giá trị', 'field': "value_import_inventory_adjustment", "type": 'number_int', "sum": True},

    # Nhap noi bo
    {"size": 8, "group": "Nhập nội bộ", "name": 'Số lượng', 'field': "qty_import_internal", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Nhập nội bộ", "name": 'Giá trị', 'field': "value_import_internal", "type": 'number_int', "sum": True},

    # Nhap khac
    {"size": 8, "group": "Nhập khác", "name": 'Số lượng', 'field': "qty_import_other", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Nhập khác", "name": 'Giá trị', 'field': "value_import_other", "type": 'number_int', "sum": True},

    # Tong nhap
    {"size": 8, "group": "Tổng nhập", "name": 'Số lượng', 'field': "qty_import_total", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Tổng nhập", "name": 'Giá trị', 'field': "value_import_total", "type": 'number_int', "sum": True},

    # Gia binh quan
    {"size": 12, "name": 'Giá bình quân', 'field': "average_price", "type": 'number_int', "sum": True},
    # Gia tri phan bo
    {"size": 12, "name": 'Giá trị phân bổ', 'field': "allocated_cost", "type": 'number_int', "sum": True},

    # Xuat ban
    {"size": 8, "group": "Xuất bán", "name": 'Số lượng', 'field': "qty_export_sale", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Xuất bán", "name": 'Doanh thu', 'field': "value_export_sale", "type": 'number_int', "sum": True},
    {"size": 12, "group": "Xuất bán", "name": 'Giá vốn', 'field': "value_export_sale_cost", "type": 'number_int', "sum": True},
    {"size": 12, "group": "Xuất bán", "name": 'Lãi gộp', 'field': "value_export_sale_profit", "type": 'number_int', "sum": True},

    # Xuat san xuat
    {"size": 8, "group": "Xuất sản xuất", "name": 'Số lượng', 'field': "qty_export_production", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Xuất sản xuất", "name": 'Giá trị', 'field': "value_export_production", "type": 'number_int', "sum": True},

    # Xuat hao hut kiem ke
    {"size": 8, "group": "Xuất hao hụt kiểm kê", "name": 'Số lượng', 'field': "qty_export_inventory_adjustment", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Xuất hao hụt kiểm kê", "name": 'Giá trị', 'field': "value_export_inventory_adjustment", "type": 'number_int', "sum": True},

    # Xuat noi bo
    {"size": 8, "group": "Xuất nội bộ", "name": 'Số lượng', 'field': "qty_export_internal", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Xuất nội bộ", "name": 'Giá trị', 'field': "value_export_internal", "type": 'number_int', "sum": True},

    # Xuat khac
    {"size": 8, "group": "Xuất khác", "name": 'Số lượng', 'field': "qty_export_other", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Xuất khác", "name": 'Giá trị', 'field': "value_export_other", "type": 'number_int', "sum": True},

    # Tong xuat
    {"size": 8, "group": "Tổng xuất", "name": 'Số lượng', 'field': "qty_export_total", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Tổng xuất", "name": 'Giá trị', 'field': "value_export_total", "type": 'number_int', "sum": True},

    # Ton cuoi ky
    {"size": 8, "group": "Tồn cuối kỳ", "name": 'Số lượng', 'field': "qty_end", "type": 'number_float3', "sum": True},
    {"size": 12, "group": "Tồn cuối kỳ", "name": 'Giá trị', 'field': "value_end", "type": 'number_int', "sum": True},

    # Kho
    {"size": 10, "name": 'Kho', 'field': "warehouse_id", "type": 'text', "sum": False},
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
        "header": format_workbook(workbook, 10, bold=True, border=1, text_wrap=True, align='center'),

        # Body Text
        "text": format_workbook(workbook, 10, border=1, align='center', text_wrap=True),
        "date": format_workbook(workbook, 10, border=1, num_format='dd/mm/yyyy', align='center', text_wrap=True),
        "datetime": format_workbook(workbook, 10, border=1, num_format='dd/mm/yyyy hh:mm:ss', align='center', text_wrap=True),

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

def get_column_letter(col_num):
    """Convert column number to Excel column letter (1=A, 2=B, etc.)"""
    result = ""
    while col_num > 0:
        col_num -= 1
        result = chr(65 + col_num % 26) + result
        col_num //= 26
    return result

class rp_summary_ie_inv_xlsx(models.AbstractModel):
    _inherit = "report.biz_stock_summary_report.rp_summary_ie_inv_xlsx"
    _description = TITLE

    def _init_sum(self):
        """Khởi tạo dictionary để tính tổng dựa trên cấu hình COLUMNS."""
        # Giả định COLUMNS là một biến có sẵn
        return {col['field']: 0 for col in COLUMNS if col.get('sum')}

    def _get_group_data(self, obj, grand_totals):
        grouped = {}
        
        # Nếu separate_warehouse_lines = True, nhóm theo warehouse trước, sau đó theo stock_valuation_account_id
        if hasattr(obj, 'separate_warehouse_lines') and obj.separate_warehouse_lines:
            # Nhóm theo warehouse
            warehouse_ids = obj.line_ids.mapped('warehouse_id')
            for warehouse_id in warehouse_ids:
                warehouse_name = warehouse_id.name if warehouse_id else 'Không xác định'
                warehouse_lines = obj.line_ids.filtered(lambda l: l.warehouse_id == warehouse_id)
                
                # Trong mỗi warehouse, nhóm theo stock_valuation_account_id
                stock_valuation_account_ids = warehouse_lines.mapped('stock_valuation_account_id')
                for stock_valuation_account_id in stock_valuation_account_ids:
                    count = 0
                    lines = []
                    sums = self._init_sum()
                    
                    filtered_lines = warehouse_lines.filtered(lambda l: l.stock_valuation_account_id == stock_valuation_account_id)
                    for line in filtered_lines:
                        line_data = line._get_data_export()
                        count += 1
                        line_data['no'] = count
                        lines.append(line_data)
                        for key in sums.keys():
                            sums[key] += line_data.get(key, 0)
                    
                    for key in grand_totals.keys():
                        grand_totals[key] += sums.get(key, 0)
                    
                    account_name = stock_valuation_account_id.display_name if stock_valuation_account_id else 'Không xác định'
                    group_name = f"{warehouse_name} - {account_name}"
                    grouped[group_name] = {
                        "lines": lines,
                        "sums": sums
                    }
        else:
            # Nhóm theo stock_valuation_account_id như cũ
            stock_valuation_account_ids = obj.line_ids.mapped('stock_valuation_account_id')
            for stock_valuation_account_id in stock_valuation_account_ids:
                count = 0
                lines = []
                sums = self._init_sum()
                for line in obj.line_ids.filtered(lambda l: l.stock_valuation_account_id == stock_valuation_account_id):
                    line_data = line._get_data_export()
                    count += 1
                    line_data['no'] = count
                    lines.append(line_data)
                    for key in sums.keys():
                        sums[key] += line_data.get(key, 0)
                for key in grand_totals.keys():
                    grand_totals[key] += sums.get(key, 0)
                group_name = stock_valuation_account_id.display_name if stock_valuation_account_id else 'Không xác định'
                grouped[group_name] = {
                    "lines": lines,
                    "sums": sums
                }
        return grouped
    
    def _get_data_export(self, obj):
        # TODO: Bạn cần viết logic lấy dữ liệu ở đây
        # Ví dụ mẫu:
        grand_totals = self._init_sum()
        
        # TODO: Thêm logic lấy dữ liệu thực tế
        grouped = self._get_group_data(obj, grand_totals) or {}
        
        return {
            "grouped": grouped,
            "grand_totals": grand_totals
        }

    def _get_visible_columns(self, obj):
        if hasattr(obj, "_ensure_column_settings"):
            obj._ensure_column_settings()
        if hasattr(obj, "column_ids") and obj.column_ids:
            visible_codes = set(obj.column_ids.filtered("is_visible").mapped("code"))
            visible_columns = [col for col in COLUMNS if col["field"] in visible_codes]
            if visible_columns:
                group_counts = {}
                for col in visible_columns:
                    group = col.get("group")
                    if group:
                        group_counts[group] = group_counts.get(group, 0) + 1
                if group_counts:
                    normalized_columns = []
                    for col in visible_columns:
                        group = col.get("group")
                        if group and group_counts.get(group, 0) == 1:
                            col = dict(col)
                            col["name"] = group
                            col.pop("group", None)
                        normalized_columns.append(col)
                    visible_columns = normalized_columns
                return visible_columns
        return COLUMNS

    def add_title(self, sheet, formats, obj, columns):
        global start_row
        
        # Keep company name and address fixed
        sheet.merge_range("C2:G2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751",formats["company_name"],)
        sheet.merge_range("C3:G3", "23 Lô B, Đường số 1, P. Phú Thuận, Q.7", formats["company_name"])
        
        # Keep image insertion as is
        sheet.insert_image("A1",get_module_resource("ccv_bao_cao", "static/src/img", "logo.png"),{"x_offset": 0, "y_offset": 0, "x_scale": 0.22, "y_scale": 0.22},)

        # Calculate the last column letter dynamically
        last_column_letter = get_column_letter(len(columns))

        # Main title
        title_text = TITLE.upper()
        sheet.merge_range(f"A{start_row}:{last_column_letter}{start_row}", title_text, formats["title_main"])
        sheet.set_row(start_row - 1, 35)
        start_row += 1
        
        # Warehouse and date info
        warehouse_ids = obj.warehouse_ids
        if obj.warehouse_id:
            warehouse_ids |= obj.warehouse_id
        
        if len(warehouse_ids) == 1:
            warehouse_text = 'Kho: ' + ', '.join(warehouse_ids.filtered(lambda w: w).mapped('name')) + '; '
        else:
            warehouse_text = ''
        
        date_text = f"Từ ngày: {obj.from_date.strftime('%d/%m/%Y')} - Đến ngày: {obj.to_date.strftime('%d/%m/%Y')}"
        info_text = f"{warehouse_text}{date_text}"
        
        sheet.merge_range(f"A{start_row}:{last_column_letter}{start_row}", info_text, formats["title_sub"])
        sheet.set_row(start_row - 1, 25)
        start_row += 1

    def add_header(self, sheet, formats, obj, columns):
        global start_row
        row_group = start_row
        start_row += 1
        row_detail = start_row

        col = 0
        last_group = None
        group_start_col = 0

        for i, column in enumerate(columns):
            group = column.get("group", "")
            name = column.get("name", "")

            if not group:
                sheet.merge_range(row_group, col, row_detail, col, name, formats["header"])
            else:
                # Ghi tiêu đề con (tên cột)
                sheet.write(row_detail, col, name, formats["header"])

                is_last = (i == len(columns) - 1)
                next_group = columns[i + 1].get("group", "") if not is_last else None

                if group != last_group:
                    group_start_col = col

                if group != next_group or is_last:
                    # Merge ngang cho group
                    sheet.merge_range(row_group, group_start_col, row_group, col, group, formats["header"])

            last_group = group
            col += 1
        
        start_row += 1  # Tăng start_row sau khi hoàn thành header

    def add_body(self, sheet, formats, obj, columns):
        def update_idx(lines_data):
            idx = 1
            for group_name, group_data in lines_data.get("grouped", {}).items():
                for line in group_data.get("lines", []):
                    line['no'] = idx
                    idx += 1
        global start_row
        lines_data = self._get_data_export(obj)
        prod_row = start_row

        # Xác định chỉ số cột đầu tiên có 'sum': True để định vị nhãn "TỔNG CỘNG"
        first_summable_col_idx = -1
        for idx, col_def in enumerate(columns):
            if col_def.get('sum'):
                first_summable_col_idx = idx
                break

        if first_summable_col_idx != -1:
            # Gộp đến cột ngay trước cột summable đầu tiên
            merge_label_col_end_idx = max(0, first_summable_col_idx - 1)
        else:
            # Nếu không có cột nào summable, gộp qua tất cả các cột
            merge_label_col_end_idx = len(columns) - 1

        # Lặp qua từng nhóm sản phẩm trong dữ liệu
        has_account = columns[1].get('field') == 'stock_valuation_account_id'
        if not has_account:
            update_idx(lines_data)

        parent_group_sums = self._init_sum()
        current_parent_key = None
        current_prefix = ""

        def write_parent_total():
            nonlocal prod_row, current_prefix, parent_group_sums
            sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx,
                            f"TỔNG CỘNG TÀI KHOẢN: {current_prefix.upper()}", formats["total_text_bold"])
            for col_idx, column_def in enumerate(columns):
                if column_def.get('sum'):
                    field_name = column_def.get('field')
                    sum_value = parent_group_sums.get(field_name, 0)
                    total_fmt_key = column_def['type'].replace('number', 'total')
                    fmt = formats.get(total_fmt_key, formats["total_int"])
                    sheet.write(prod_row, col_idx, sum_value, fmt)
                elif col_idx > merge_label_col_end_idx:
                    sheet.write(prod_row, col_idx, "", formats["text"])
            prod_row += 1

        for group_name, group_data in lines_data.get("grouped", {}).items():
            if has_account:
                first_line = group_data.get("lines", [])[0] if group_data.get("lines") else {}
                account_str = str(first_line.get('stock_valuation_account_id', ''))
                warehouse_str = str(first_line.get('warehouse_id', ''))
                prefix = account_str[:3]
                parent_key = (warehouse_str, prefix)

                if current_parent_key is None:
                    current_parent_key = parent_key
                    current_prefix = prefix
                elif current_parent_key != parent_key:
                    write_parent_total()
                    current_parent_key = parent_key
                    current_prefix = prefix
                    parent_group_sums = self._init_sum()

                sums = group_data.get("sums", {})
                for k in parent_group_sums:
                    parent_group_sums[k] = parent_group_sums.get(k, 0) + sums.get(k, 0)

            # Ghi tiêu đề tên nhóm
            if has_account:
                sheet.merge_range(prod_row, 0, prod_row, len(columns) - 1,
                                f"{group_name.upper()}", formats["total_text_bold"])
                prod_row += 1

            # Ghi các dòng dữ liệu chi tiết cho nhóm hiện tại
            current_group_lines = group_data.get("lines", [])
            for row in current_group_lines:
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
            
            if has_account:
                # Ghi dòng tổng cộng cho nhóm hiện tại (Sub-Total)
                sums = group_data.get("sums", {})
                
                # Nhãn "TỔNG CỘNG: [Tên nhóm]"
                sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                                f"TỔNG CỘNG: {group_name.upper()}", formats["total_text_bold"])
                
                # Ghi tổng của từng cột summable cho nhóm hiện tại
                for col_idx, column_def in enumerate(columns):
                    if column_def.get('sum'):
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

        if has_account and current_parent_key is not None:
            write_parent_total()

        # --- Phần Tổng Cộng Chung (Grand Total) ---
        grand_totals = lines_data.get("grand_totals", {})
        
        # Nhãn "TỔNG CỘNG TẤT CẢ NHÓM"
        sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                          "TỔNG CỘNG%s" % (" TẤT CẢ NHÓM" if has_account else ""), formats["total_text_bold"])
        
        # Ghi tổng của từng cột summable cho tất cả các nhóm
        for col_idx, column_def in enumerate(columns):
            if column_def.get('sum'):
                field_name = column_def.get('field')
                sum_value = grand_totals.get(field_name, 0)
                
                # Xác định định dạng tổng phù hợp
                total_fmt_key = column_def['type'].replace('number', 'total')
                fmt = formats.get(total_fmt_key, formats["total_int"]) 

                sheet.write(prod_row, col_idx, sum_value, fmt)
            elif col_idx > merge_label_col_end_idx: # Điền ô trống cho các cột không summable sau nhãn
                sheet.write(prod_row, col_idx, "", formats["text"])
        prod_row += 1
        start_row = prod_row + 2

    def add_signatures(self, sheet, formats, obj, columns):
        global start_row
        row = start_row

        last_column_index = len(columns) - 1
        total_columns = len(columns) 

        date_merge_start_col_idx = max(0, last_column_index - 2)
        date_merge_end_col_idx = last_column_index

        date_merge_start_col_letter = get_column_letter(date_merge_start_col_idx + 1)
        date_merge_end_col_letter = get_column_letter(date_merge_end_col_idx + 1)

        sheet.merge_range(f"{date_merge_start_col_letter}{row}:{date_merge_end_col_letter}{row}", "Ngày ..... tháng ..... năm .........", formats["signature_date"])

        row += 1 

        signature_blocks = [
            {"role": "Người Lập Biểu", "signer": obj.voter_id.name_without_position if hasattr(obj, 'voter_id') and obj.voter_id else ""},
            {"role": "Kế toán trưởng", "signer": obj.chief_finance_id.name_without_position if hasattr(obj, 'chief_finance_id') and obj.chief_finance_id else ""},
            {"role": "Người ký duyệt", "signer": obj.director_id.name_without_position if hasattr(obj, 'director_id') and obj.director_id else ""},
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

            col_from_letter = get_column_letter(col_start_idx + 1)
            col_to_letter = get_column_letter(col_end_idx + 1)

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

            col_from_letter = get_column_letter(col_start_idx + 1)
            col_to_letter = get_column_letter(col_end_idx + 1)

            sheet.merge_range(f"{col_from_letter}{row}:{col_to_letter}{row}", block["signer"], formats["signature_name"])

            current_col_idx = col_end_idx + 1

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, obj, objects):
        global start_row
        for obj in objects.sudo():
            start_row = 4  # Bắt đầu từ dòng 4 (sau logo và thông tin công ty)
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE,"author": self.env.user.name_without_position,})
            sheet.set_landscape()
            formats = create_formats(workbook)
            columns = self._get_visible_columns(obj)
            self.add_title(sheet, formats, obj, columns)
            self.add_header(sheet, formats, obj, columns)
            self.add_body(sheet, formats, obj, columns)
            self.add_signatures(sheet, formats, obj, columns)
