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
TITLE = 'Báo cáo doanh số khu vực'


COLUMNS = [
    {"size":  5,                                "name": 'STT'                 , 'field':"no"                              , "type": 'number_c_int'      , "sum": False  },
    {"size": 20,  "group": "KHU VỰC",           "name": 'KHU VỰC'             , 'field':"region_name"                     , "type": 'text'              , "sum": False  },
    {"size": 20,                                "name": 'TỈNH/TP'             , 'field':"state_name"                      , "type": 'text'              , "sum": False  },
    {"size": 12,  "group": "DOANH SỐ",          "name": 'KẾ HOẠCH'            , 'field':"planned_quantity"                , "type": 'number_float2'     , "sum": True  },
    {"size": 12,  "group": "DOANH SỐ",          "name": 'THỰC HIỆN'           , 'field':"production_quantity"             , "type": 'number_float2'     , "sum": True  },
    {"size": 10,  "group": "DOANH SỐ",          "name": 'TL %'                , 'field':"sales_percentage"                , "type": 'number_float2'     , "sum": True  },
    {"size": 12,  "group": "DOANH THU",         "name": 'Bán hàng'            , 'field':"total_revenue"                   , "type": 'number_int'        , "sum": True  },
    {"size": 12,  "group": "DOANH THU",         "name": 'Thu tiền'            , 'field':"total_payment_received"          , "type": 'number_int'        , "sum": True  },
    {"size": 10,  "group": "DOANH THU",         "name": 'TL %'                , 'field':"revenue_percentage"              , "type": 'number_float2'     , "sum": True  },
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

        # Invoice line format (vàng nhẹ background, chữ đỏ)
        "invoice_text": format_workbook(workbook, 11.5, border=1, align='center', text_wrap=True, font_color='red', fg_color='#FFFFE0'),
        "invoice_number_int": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0", font_color='red', fg_color='#FFFFE0'),
        "invoice_number_float2": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0.00", font_color='red', fg_color='#FFFFE0'),
        "invoice_number_float3": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0.000", font_color='red', fg_color='#FFFFE0'),

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


class RpRegionalSalesReport(models.AbstractModel):
    _name = "report.biz_kpi_business_salary.rp_regional_sales"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE
    
    def _init_sum(self):
        """Khởi tạo dictionary để tính tổng dựa trên cấu hình COLUMNS."""
        return {col['field']: 0 for col in COLUMNS if col.get('sum')}
    
    def _calculate_percentages(self, data_dict):
        """Tính toán phần trăm cho dữ liệu"""
        if data_dict.get("planned_quantity", 0) > 0:
            data_dict["sales_percentage"] = float((data_dict.get("production_quantity", 0) / data_dict.get("planned_quantity", 0)) * 100)
        else:
            data_dict["sales_percentage"] = 0.0
        
        if data_dict.get("total_revenue", 0) > 0:
            data_dict["revenue_percentage"] = float((data_dict.get("total_payment_received", 0) / data_dict.get("total_revenue", 0)) * 100)
        else:
            data_dict["revenue_percentage"] = 0.0
    
    def _get_data_export(self, obj):
        """Lấy dữ liệu từ salary.sales.summary.line và nhóm theo khu vực"""
        line_ids = obj.line_ids.filtered(lambda l: 'Thương mại' not in l.team_id.name)
        lines_data = line_ids.filtered(lambda l: l.planned_quantity > 0 or l.total_revenue > 0 or l.total_payment_received > 0 or l.production_quantity > 0)
        lines_data = lines_data.sorted(lambda l: (l.team_id.id or 0, l.planned_quantity or 0, l.total_revenue or 0, l.total_payment_received or 0), reverse=True)
        
        # Lấy mapping is_apply_pre_invoice từ total_line_ids theo team_id
        total_lines = obj.total_line_ids
        is_apply_pre_invoice_map = {tl.team_id.id: tl.is_apply_pre_invoice for tl in total_lines if tl.team_id}
        
        grouped = {}
        grand_totals = self._init_sum()
        grand_invoice_total = 0  # Tổng xuất hóa đơn trước cho tất cả khu vực
        grand_invoice_quantity = 0  # Tổng số lượng xuất hóa đơn trước cho tất cả khu vực
        
        current_region = None
        region_lines = []
        region_sums = self._init_sum()
        region_invoice_total = 0  # Tổng xuất hóa đơn trước cho khu vực hiện tại
        region_invoice_quantity = 0  # Tổng số lượng xuất hóa đơn trước cho khu vực hiện tại
        region_original_lines = []  # Lưu các line gốc để tính tỷ lệ từ model
        region_team_id = None  # Lưu team_id của khu vực hiện tại
        count = 0  # STT sẽ reset về 0 cho mỗi khu vực mới
        
        for line in lines_data:
            # Kiểm tra nếu chuyển sang khu vực mới
            region_name = line.team_id.report_name if line.team_id else ''
            if current_region is not None and current_region != region_name:
                # Lưu khu vực trước đó
                if region_lines:
                    # Lấy is_apply_pre_invoice cho khu vực trước đó
                    is_apply_pre_invoice = is_apply_pre_invoice_map.get(region_team_id, False) if region_team_id else False
                    
                    # Lưu region_sums chưa trừ invoice để cộng vào grand_totals
                    region_sums_before_invoice = region_sums.copy()
                    
                    # Trừ xuất hóa đơn trước khỏi tổng khu vực chỉ nếu is_apply_pre_invoice là False
                    if not is_apply_pre_invoice:
                        region_sums["production_quantity"] = max(0, region_sums.get("production_quantity", 0) - region_invoice_quantity)
                        region_sums["total_revenue"] = max(0, region_sums.get("total_revenue", 0) - region_invoice_total)
                    
                    # Tính phần trăm cho tổng khu vực từ region_sums (đã trừ invoice)
                    total_planned = region_sums.get("planned_quantity", 0)
                    total_production = region_sums.get("production_quantity", 0)
                    total_revenue = region_sums.get("total_revenue", 0)
                    total_payment = region_sums.get("total_payment_received", 0)
                    
                    if total_planned > 0:
                        region_sums["sales_percentage"] = float((total_production / total_planned) * 100)
                    else:
                        region_sums["sales_percentage"] = 0.0
                    
                    if total_revenue > 0:
                        region_sums["revenue_percentage"] = float((total_payment / total_revenue) * 100)
                    else:
                        region_sums["revenue_percentage"] = 0.0
                    
                    grouped[current_region] = {
                        "lines": region_lines,
                        "sums": region_sums.copy(),
                        "invoice_total": region_invoice_total,
                        "invoice_quantity": region_invoice_quantity,
                        "is_apply_pre_invoice": is_apply_pre_invoice
                    }
                    # Cộng vào grand totals từ region_sums chưa trừ invoice (sẽ trừ sau ở tổng chung)
                    for key in grand_totals.keys():
                        grand_totals[key] += region_sums_before_invoice.get(key, 0)
                    grand_invoice_total += region_invoice_total
                    grand_invoice_quantity += region_invoice_quantity
                
                # Khởi tạo lại cho khu vực mới
                region_lines = []
                region_sums = self._init_sum()
                region_invoice_total = 0
                region_invoice_quantity = 0
                region_original_lines = []
                region_team_id = None
                count = 0  # Reset STT về 0 cho khu vực mới
            
            current_region = region_name
            if line.team_id:
                region_team_id = line.team_id.id
            
            # Tính toán phần trăm cho từng dòng
            count += 1  # Tăng STT trước khi tạo line_data
            
            # Tính số lượng từ invoice lines (quantity đã chạy)
            invoice_lines = line.detail_line_ids.filtered(lambda l: l.line_type == 'invoice')
            invoice_quantity = sum(invoice_lines.mapped('quantity') or [])
            
            # Từng dòng giữ nguyên giá trị gốc (KHÔNG trừ invoice ở đây)
            line_data = {
                "no": count,  # STT bắt đầu từ 1 cho mỗi khu vực
                "region_name": region_name,
                "state_name": line.state_id.name if line.state_id else '',
                "planned_quantity": line.planned_quantity or 0,
                "production_quantity": line.production_quantity or 0,  # Giữ nguyên giá trị gốc
                "total_revenue": line.total_revenue or 0,  # Giữ nguyên giá trị gốc
                "total_payment_received": line.total_payment_received or 0,
            }
            self._calculate_percentages(line_data)
            
            region_lines.append(line_data)
            region_original_lines.append(line)  # Lưu line gốc
            # Lưu lại invoice_total và invoice_quantity để trừ ở tổng
            region_invoice_total += line.total_invoice_amount or 0
            region_invoice_quantity += invoice_quantity
            
            # Cộng vào tổng khu vực (chỉ các field có sum=True trong COLUMNS)
            # Tổng này chưa trừ invoice, sẽ trừ sau khi tính xong tất cả các dòng
            for key in region_sums.keys():
                region_sums[key] += line_data.get(key, 0)
        
        # Lưu khu vực cuối cùng
        if region_lines:
            # Lấy is_apply_pre_invoice cho khu vực cuối cùng
            is_apply_pre_invoice = is_apply_pre_invoice_map.get(region_team_id, False) if region_team_id else False
            
            # Lưu region_sums chưa trừ invoice để cộng vào grand_totals
            region_sums_before_invoice = region_sums.copy()
            
            # Trừ xuất hóa đơn trước khỏi tổng khu vực chỉ nếu is_apply_pre_invoice là False
            if not is_apply_pre_invoice:
                region_sums["production_quantity"] = max(0, region_sums.get("production_quantity", 0) - region_invoice_quantity)
                region_sums["total_revenue"] = max(0, region_sums.get("total_revenue", 0) - region_invoice_total)
            
            # Tính phần trăm cho tổng khu vực từ region_sums (đã trừ invoice)
            total_planned = region_sums.get("planned_quantity", 0)
            total_production = region_sums.get("production_quantity", 0)
            total_revenue = region_sums.get("total_revenue", 0)
            total_payment = region_sums.get("total_payment_received", 0)
            
            if total_planned > 0:
                region_sums["sales_percentage"] = float((total_production / total_planned) * 100)
            else:
                region_sums["sales_percentage"] = 0.0
            
            if total_revenue > 0:
                region_sums["revenue_percentage"] = float((total_payment / total_revenue) * 100)
            else:
                region_sums["revenue_percentage"] = 0.0
            
            grouped[current_region] = {
                "lines": region_lines,
                "sums": region_sums.copy(),
                "invoice_total": region_invoice_total,
                "invoice_quantity": region_invoice_quantity,
                "is_apply_pre_invoice": is_apply_pre_invoice
            }
            # Cộng vào grand totals từ region_sums chưa trừ invoice (sẽ trừ sau ở tổng chung)
            for key in grand_totals.keys():
                grand_totals[key] += region_sums_before_invoice.get(key, 0)
            grand_invoice_total += region_invoice_total
            grand_invoice_quantity += region_invoice_quantity
        
        # Tính tổng is_apply_pre_invoice để quyết định có trừ invoice ở grand total không
        # Chỉ trừ nếu tất cả các khu vực đều có is_apply_pre_invoice = False
        # Nhưng để đơn giản, ta sẽ trừ invoice từ các khu vực có is_apply_pre_invoice = False
        # Tính lại grand_totals dựa trên các region đã trừ invoice
        grand_totals = self._init_sum()
        grand_invoice_total = 0
        grand_invoice_quantity = 0
        for region_name, region_data in grouped.items():
            for key in grand_totals.keys():
                grand_totals[key] += region_data.get("sums", {}).get(key, 0)
            grand_invoice_total += region_data.get("invoice_total", 0)
            grand_invoice_quantity += region_data.get("invoice_quantity", 0)
        
        # Tính phần trăm cho grand total từ grand_totals (đã trừ invoice từ tất cả khu vực)
        total_planned_all = grand_totals.get("planned_quantity", 0)
        total_production_all = grand_totals.get("production_quantity", 0)
        total_revenue_all = grand_totals.get("total_revenue", 0)
        total_payment_all = grand_totals.get("total_payment_received", 0)
        
        if total_planned_all > 0:
            grand_totals["sales_percentage"] = float((total_production_all / total_planned_all) * 100)
        else:
            grand_totals["sales_percentage"] = 0.0
        
        if total_revenue_all > 0:
            grand_totals["revenue_percentage"] = float((total_payment_all / total_revenue_all) * 100)
        else:
            grand_totals["revenue_percentage"] = 0.0
        
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

        replace_zeros(grouped)
        replace_zeros(grand_totals)

        return {
            "grouped": grouped,
            "grand_totals": grand_totals,
            "grand_invoice_total": grand_invoice_total,
            "grand_invoice_quantity": grand_invoice_quantity
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
        row_group = 5 if obj.month and obj.year else 5
        row_detail = 6 if obj.month and obj.year else 6
        
        # Điều chỉnh nếu có dòng tháng/năm
        if obj.month and obj.year:
            row_group = 6
            row_detail = 7

        col = 0
        last_group = None
        group_start_col = 0

        for i, column in enumerate(COLUMNS):
            group = column.get("group", "")
            name = column.get("name", "")
            field = column.get("field", "")

            if not group:
                # Merge 2 dòng cho các cột không có group (STT, TỈNH/TP)
                sheet.merge_range(row_group, col, row_detail, col, name, formats["header"])
            else:
                # Đặc biệt: cột KHU VỰC (region_name) cũng merge 2 dòng
                if field == "region_name":
                    sheet.merge_range(row_group, col, row_detail, col, name, formats["header"])
                else:
                    # Ghi tiêu đề con (tên cột) cho các cột trong group
                    sheet.write(row_detail, col, name, formats["header"])

                is_last = (i == len(COLUMNS) - 1)
                next_group = COLUMNS[i + 1].get("group", "") if not is_last else None

                if group != last_group:
                    group_start_col = col

                if group != next_group or is_last:
                    # Merge ngang cho group (chỉ merge ở dòng group, không merge với dòng detail)
                    sheet.merge_range(row_group, group_start_col, row_group, col, group, formats["header"])

            last_group = group
            col += 1

    def add_body(self, sheet, formats, obj, workbook):
        lines_data = self._get_data_export(obj)
        prod_row = 7 if obj.month and obj.year else 7
        
        # Điều chỉnh nếu có dòng tháng/năm
        if obj.month and obj.year:
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

        # Tìm chỉ số cột KHU VỰC (region_name)
        region_col_idx = None
        for idx, col_def in enumerate(COLUMNS):
            if col_def.get('field') == 'region_name':
                region_col_idx = idx
                break
        
        # Lặp qua từng khu vực trong dữ liệu
        for region_name, region_data in lines_data.get("grouped", {}).items():
            # Ghi các dòng dữ liệu chi tiết cho khu vực hiện tại
            current_region_lines = region_data.get("lines", [])
            region_start_row = prod_row
            region_end_row = prod_row + len(current_region_lines) - 1
            
            for row_idx, row in enumerate(current_region_lines):
                for col_idx, column_def in enumerate(COLUMNS):
                    sheet.set_column(col_idx, col_idx, column_def.get('size', 10))
                    fmt = formats[column_def.get('type', 'text')]
                    
                    field_name = column_def.get('field')
                    cell_value = row.get(field_name)

                    # Xử lý đặc biệt cho cột KHU VỰC - chỉ ghi ở dòng đầu tiên của khu vực
                    if field_name == 'region_name':
                        if row_idx == 0:
                            # Ghi giá trị ở dòng đầu, sau đó sẽ merge
                            sheet.write(prod_row, col_idx, cell_value, fmt)
                        # Các dòng khác sẽ để trống, sẽ được merge sau
                    else:
                        # Xử lý đặc biệt cho kiểu ngày/thời gian
                        if column_def.get('type') == 'date' and isinstance(cell_value, datetime):
                            cell_value = cell_value.date()
                        elif column_def.get('type') == 'datetime' and isinstance(cell_value, datetime):
                            pass # xlsxwriter tự xử lý đối tượng datetime với num_format

                        sheet.write(prod_row, col_idx, cell_value, fmt)
                prod_row += 1
            
            # Merge cột KHU VỰC cho các dòng cùng khu vực (nếu có nhiều hơn 1 dòng)
            if region_col_idx is not None and len(current_region_lines) > 1:
                # Lấy giá trị từ dòng đầu tiên đã ghi
                region_value = current_region_lines[0].get('region_name', '')
                sheet.merge_range(region_start_row, region_col_idx, region_end_row, region_col_idx, 
                                region_value, formats["text"])
            
            # Ghi dòng "Xuất hóa đơn trước" trước dòng tổng cộng
            # LƯU Ý: Dòng này CHỈ hiển thị thông tin, KHÔNG được tính vào tổng cộng
            # vì invoice_total không nằm trong region_sums (chỉ các field có sum=True mới được cộng)
            invoice_total = region_data.get("invoice_total", 0)
            invoice_quantity = region_data.get("invoice_quantity", 0)
            is_apply_pre_invoice = region_data.get("is_apply_pre_invoice", False)
            
            if invoice_total or invoice_quantity:
                invoice_row = prod_row
                # Nếu is_apply_pre_invoice là False, hiển thị số âm
                display_invoice_total = -invoice_total if not is_apply_pre_invoice else invoice_total
                display_invoice_quantity = -invoice_quantity if not is_apply_pre_invoice else invoice_quantity
                
                for col_idx, column_def in enumerate(COLUMNS):
                    field_name = column_def.get('field')
                    # Sử dụng format đặc biệt cho dòng invoice (vàng nhẹ, chữ đỏ)
                    if column_def.get('type') == 'number_int':
                        fmt = formats["invoice_number_int"]
                    elif column_def.get('type') == 'number_float2':
                        fmt = formats["invoice_number_float2"]
                    elif column_def.get('type') == 'number_float3':
                        fmt = formats["invoice_number_float3"]
                    else:
                        fmt = formats["invoice_text"]
                    
                    if field_name == 'no':
                        # STT: để trống
                        sheet.write(invoice_row, col_idx, "", fmt)
                    elif field_name == 'region_name':
                        # KHU VỰC: để trống
                        sheet.write(invoice_row, col_idx, "", fmt)
                    elif field_name == 'state_name':
                        # TỈNH/TP: "Xuất hóa đơn trước"
                        sheet.write(invoice_row, col_idx, "Xuất hóa đơn trước", fmt)
                    elif field_name == 'planned_quantity':
                        # DOANH SỐ - KẾ HOẠCH: để trống
                        sheet.write(invoice_row, col_idx, "", fmt)
                    elif field_name == 'production_quantity':
                        # DOANH SỐ - THỰC HIỆN: số lượng từ invoice lines (có thể âm)
                        sheet.write(invoice_row, col_idx, display_invoice_quantity, fmt)
                    elif field_name == 'sales_percentage':
                        # DOANH SỐ - TL %: để trống (vì không có kế hoạch)
                        sheet.write(invoice_row, col_idx, "", fmt)
                    elif field_name == 'total_revenue':
                        # DOANH THU - Bán hàng: total_invoice_amount (có thể âm)
                        sheet.write(invoice_row, col_idx, display_invoice_total, fmt)
                    elif field_name == 'total_payment_received':
                        # DOANH THU - Thu tiền: để trống
                        sheet.write(invoice_row, col_idx, "", fmt)
                    elif field_name == 'revenue_percentage':
                        # DOANH THU - TL %: để trống (vì không có thu tiền)
                        sheet.write(invoice_row, col_idx, "", fmt)
                    else:
                        sheet.write(invoice_row, col_idx, "", fmt)
                prod_row += 1
            
            # Ghi dòng tổng cộng cho khu vực hiện tại (Sub-Total)
            sums = region_data.get("sums", {})
            
            # Nhãn "TỔNG CỘNG KHU VỰC: [Tên khu vực]"
            sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                              f"TỔNG CỘNG: {region_name.upper()}", formats["total_text_bold"])
            
            # Ghi tổng của từng cột summable cho khu vực hiện tại
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
            # Đặt height = 30 cho dòng tổng cộng khu vực
            sheet.set_row(prod_row)
            prod_row += 1 # Chuyển sang dòng tiếp theo

        # --- Phần Tổng Cộng Chung (Grand Total) ---
        grand_totals = lines_data.get("grand_totals", {})
        grand_invoice_total = lines_data.get("grand_invoice_total", 0)
        grand_invoice_quantity = lines_data.get("grand_invoice_quantity", 0)
        
        # Tính tổng is_apply_pre_invoice: nếu có ít nhất một khu vực có is_apply_pre_invoice = True
        # thì không hiển thị số âm ở grand total (nhưng vẫn hiển thị số dương)
        # Để đơn giản, ta sẽ hiển thị tổng số dương ở grand total
        # Nhưng nếu tất cả các khu vực đều có is_apply_pre_invoice = False, thì hiển thị số âm
        all_regions_apply_pre_invoice = all(region_data.get("is_apply_pre_invoice", False) 
                                             for region_data in lines_data.get("grouped", {}).values())
        display_grand_invoice_total = grand_invoice_total if all_regions_apply_pre_invoice else -grand_invoice_total
        display_grand_invoice_quantity = grand_invoice_quantity if all_regions_apply_pre_invoice else -grand_invoice_quantity
        
        # Ghi dòng "Xuất hóa đơn trước" cho grand total (format giống dòng tổng cộng)
        if grand_invoice_total or grand_invoice_quantity:
            invoice_row = prod_row
            # Nhãn "Xuất hóa đơn trước" (merge các cột đầu) - format đặc biệt
            invoice_label_fmt = format_workbook(workbook, 10, border=1, bold=True, text_wrap=True, align="left", font_color='red', fg_color='#FFFFE0')
            sheet.merge_range(invoice_row, 0, invoice_row, merge_label_col_end_idx, 
                            "Tổng cộng Xuất hóa đơn trước".upper(), invoice_label_fmt)
            
            for col_idx, column_def in enumerate(COLUMNS):
                field_name = column_def.get('field')
                
                # Sử dụng format đặc biệt cho dòng invoice (vàng nhẹ, chữ đỏ)
                if column_def.get('type') == 'number_int':
                    fmt = formats["invoice_number_int"]
                elif column_def.get('type') == 'number_float2':
                    fmt = formats["invoice_number_float2"]
                elif column_def.get('type') == 'number_float3':
                    fmt = formats["invoice_number_float3"]
                else:
                    fmt = formats["invoice_text"]
                
                if col_idx <= merge_label_col_end_idx:
                    # Các cột đã được merge trong nhãn, bỏ qua
                    continue
                elif field_name == 'planned_quantity':
                    # DOANH SỐ - KẾ HOẠCH: để trống
                    sheet.write(invoice_row, col_idx, "", fmt)
                elif field_name == 'production_quantity':
                    # DOANH SỐ - THỰC HIỆN: số lượng từ invoice lines (có thể âm)
                    sheet.write(invoice_row, col_idx, display_grand_invoice_quantity, fmt)
                elif field_name == 'sales_percentage':
                    # DOANH SỐ - TL %: để trống (vì không có kế hoạch)
                    sheet.write(invoice_row, col_idx, "", fmt)
                elif field_name == 'total_revenue':
                    # DOANH THU - Bán hàng: grand_invoice_total (có thể âm)
                    sheet.write(invoice_row, col_idx, display_grand_invoice_total, fmt)
                elif field_name == 'total_payment_received':
                    # DOANH THU - Thu tiền: để trống
                    sheet.write(invoice_row, col_idx, "", fmt)
                elif field_name == 'revenue_percentage':
                    # DOANH THU - TL %: để trống (vì không có thu tiền)
                    sheet.write(invoice_row, col_idx, "", fmt)
                else:
                    sheet.write(invoice_row, col_idx, "", fmt)
            prod_row += 1
        
        # Nhãn "TỔNG CỘNG TẤT CẢ KHU VỰC"
        sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                          "TỔNG CỘNG TẤT CẢ KHU VỰC", formats["total_text_bold"])
        
        # Ghi tổng của từng cột summable cho tất cả các khu vực
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
        # Đặt height = 30 cho dòng tổng cộng tất cả khu vực
        sheet.set_row(prod_row)
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
            {"role": "Người Lập", "signer": obj.voter_id.name_without_position or obj.voter_id.name or ''},
            {"role": "Phòng Kinh doanh", "signer": obj.lead_sale_id.name_without_position or obj.lead_sale_id.name or ''},
            {"role": "Phòng Kế toán", "signer": obj.chief_finance_id.name_without_position or obj.chief_finance_id.name or ''},
            {"role": "Thủ trưởng đơn vị", "signer": obj.director_id.name_without_position or obj.director_id.name or ''},
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
            obj = obj.sudo()
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE,"author": self.env.user.name_without_position if hasattr(self.env.user, 'name_without_position') else self.env.user.name,})
            sheet.set_landscape()
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj, workbook)
            self.add_signatures(sheet, formats, obj)
