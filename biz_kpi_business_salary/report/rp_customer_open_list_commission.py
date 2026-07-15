# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models
from odoo.modules.module import get_module_resource

import xlsxwriter
import ast
import json
import logging

_logger = logging.getLogger(__name__)
TITLE = 'BẢNG TÍNH CHI TIẾT HOA HỒNG MỞ ĐẠI LÝ MỚI'


COLUMNS = [
    {"size": 8,  "name": 'STT'                      , 'field':"no"                  , "type": 'text_center'       , "sum": False  },
    {"size": 20, "name": 'Khu vực'                  , 'field':"region_name"         , "type": 'text_center'       , "sum": False  },
    {"size": 20, "name": 'Mã khách hàng'            , 'field':"customer_code"       , "type": 'text_center'       , "sum": False  },
    {"size": 30, "name": 'Tên khách hàng'           , 'field':"customer_name"       , "type": 'text'              , "sum": False  },
    {"size": 12, "name": 'Số lượng'                 , 'field':"quantity"            , "type": 'number_float2'     , "sum": True   },
    {"size": 20, "name": 'Nhân viên phụ trách'      , 'field':"person_in_charge"    , "type": 'text_center'       , "sum": False  },
    {"size": 18, "name": 'Đơn giá tính hoa hồng'    , 'field':"unit_price"          , "type": 'number_int'        , "sum": False  },
    {"size": 10, "name": 'Tỷ lệ'                    , 'field':"achievement_rate"    , "type": 'number_float2'     , "sum": False  },
    {"size": 18, "name": 'Thành tiền'               , 'field':"commission_amount"   , "type": 'number_int'        , "sum": True   },
]

def format_workbook(workbook, font_size, font_name="Times New Roman", **kwargs):
    """
    Tạo định dạng Excel linh hoạt bằng xlsxwriter.
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
        "header": format_workbook(workbook, 11, bold=True, border=1, text_wrap=True, align='center', fg_color='#D9E1F2'),

        # Body Text
        "text": format_workbook(workbook, 11.5, border=1, align='left', text_wrap=True),
        "text_center": format_workbook(workbook, 11.5, border=1, align='center', text_wrap=True),
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


class RpCustomerOpenListCommissionReport(models.AbstractModel):
    _name = "report.biz_kpi_business_salary.rp_customer_open_list_commission"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE
    
    def _init_sum(self):
        """Khởi tạo dictionary để tính tổng dựa trên cấu hình COLUMNS."""
        return {col['field']: 0 for col in COLUMNS if col.get('sum')}
    
    def _get_data_export(self, obj):
        """Lấy dữ liệu từ salary.customer.open.list và nhóm theo khu vực"""
        lines_data = obj.customer_open_list_ids.sorted(lambda l: (l.team_id.id or 0, l.partner_id.name or ''))
        
        grouped = {}
        grand_totals = self._init_sum()
        
        current_region = None
        region_lines = []
        region_sums = self._init_sum()
        count = 0
        
        for line in lines_data:
            # Kiểm tra nếu chuyển sang khu vực mới
            region_name = line.team_name or (line.team_id.report_name if line.team_id else '')
            if current_region is not None and current_region != region_name:
                # Lưu khu vực trước đó
                if region_lines:
                    grouped[current_region] = {
                        "lines": region_lines,
                        "sums": region_sums.copy(),
                    }
                    # Cộng vào grand totals
                    for key in grand_totals.keys():
                        grand_totals[key] += region_sums.get(key, 0)
                
                # Khởi tạo lại cho khu vực mới
                region_lines = []
                region_sums = self._init_sum()
                count = 0
            
            current_region = region_name
            
            # Tính tỷ lệ phần trăm
            achievement_rate_percent = (line.achievement_rate or 0) * 100 if line.achievement_rate else 0
            
            count += 1
            line_data = {
                "no": count,
                "region_name": region_name,
                "customer_code": line.partner_id.code_contact or '',
                "customer_name": line.partner_id.name or '',
                "quantity": line.quantity or 0,
                "person_in_charge": line.user_id.name_without_position or '',
                "unit_price": line.unit_price or 0,
                "achievement_rate": achievement_rate_percent,
                "commission_amount": line.commission_amount or 0,
            }
            
            region_lines.append(line_data)
            
            # Cộng vào tổng khu vực
            for key in region_sums.keys():
                region_sums[key] += line_data.get(key, 0)
        
        # Lưu khu vực cuối cùng
        if region_lines:
            grouped[current_region] = {
                "lines": region_lines,
                "sums": region_sums.copy(),
            }
            # Cộng vào grand totals
            for key in grand_totals.keys():
                grand_totals[key] += region_sums.get(key, 0)
        
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
            col += 1

    def add_body(self, sheet, formats, obj, workbook):
        lines_data = self._get_data_export(obj)
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
        merge_label_col_end_idx = 0 
        if first_summable_col_idx != -1:
            merge_label_col_end_idx = max(0, first_summable_col_idx - 1)
        else: 
            merge_label_col_end_idx = len(COLUMNS) - 1

        # Tìm chỉ số cột KHU VỰC
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
                            sheet.write(prod_row, col_idx, cell_value, fmt)
                    else:
                        # Xử lý đặc biệt cho kiểu ngày/thời gian
                        if column_def.get('type') == 'date' and isinstance(cell_value, datetime):
                            cell_value = cell_value.date()
                        elif column_def.get('type') == 'datetime' and isinstance(cell_value, datetime):
                            pass

                        sheet.write(prod_row, col_idx, cell_value, fmt)
                prod_row += 1
            
            # Merge cột KHU VỰC cho các dòng cùng khu vực (nếu có nhiều hơn 1 dòng)
            if region_col_idx is not None and len(current_region_lines) > 1:
                region_value = current_region_lines[0].get('region_name', '')
                sheet.merge_range(region_start_row, region_col_idx, region_end_row, region_col_idx, 
                                region_value, formats["text"])
            
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
                    fmt = formats.get(total_fmt_key, formats["total_int"]) 

                    sheet.write(prod_row, col_idx, sum_value, fmt)
                elif col_idx > merge_label_col_end_idx:
                    sheet.write(prod_row, col_idx, "", formats["text"])
            sheet.set_row(prod_row)
            prod_row += 1

        # --- Phần Tổng Cộng Chung (Grand Total) ---
        grand_totals = lines_data.get("grand_totals", {})
        
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
            elif col_idx > merge_label_col_end_idx:
                sheet.write(prod_row, col_idx, "", formats["text"])
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
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE,"author": self.env.user.name_without_position if hasattr(self.env.user, 'name_without_position') else self.env.user.name,})
            sheet.set_landscape()
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj, workbook)
            self.add_signatures(sheet, formats, obj)

