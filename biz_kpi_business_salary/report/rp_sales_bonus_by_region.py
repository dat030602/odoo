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
TITLE = 'BÁO CÁO DOANH SỐ THƯỞNG THEO KHU VỰC'

# Định nghĩa cột cho bảng 1: Thưởng bán hàng theo doanh số của các Khu vực
TABLE1_COLUMNS = [
    {"size":  5,  "name": 'STT'                     , 'field':"no"                          , "type": 'number_c_int'      , "sum": False  },
    {"size": 27,  "name": 'Khu vực'                 , 'field':"region_name"                 , "type": 'text'              , "sum": False  },
    {"size": 12,  "name": 'Thưởng khu vực'          , 'field':"team_commission"             , "type": 'number_int'        , "sum": True   },
    {"size": 12,  "name": 'Ban lãnh đạo'            , 'field':"leadership_commission"       , "type": 'number_int'        , "sum": True   },
    {"size": 12,  "name": 'Các phòng ban'           , 'field':"department_commission"       , "type": 'number_int'        , "sum": True   },
    {"size": 12,  "name": 'Tổng cộng'               , 'field':"total_commission"            , "type": 'number_int'        , "sum": True   },
]

# Định nghĩa cột cho bảng 2: Tiền thưởng theo doanh số
TABLE2_COLUMNS = [
    {"size":  5,  "name": 'STT'                     , 'field':"no"                        , "type": 'number_c_int'      , "sum": False  },
    {"size": 27,  "name": 'Khu vực'                 , 'field':"region_name"               , "type": 'text'              , "sum": False  },
    {"size": 12,  "name": 'Tổng tiền thưởng'        , 'field':"team_commission_amount"    , "type": 'number_int'   , "sum": True   },
    {"size": 12,  "name": 'Sale hỗ trợ'             , 'field':"sale_support_amount"       , "type": 'number_int'        , "sum": True   },
    {"size": 12,  "name": 'Trưởng khu vực'          , 'field':"team_leader_amount"        , "type": 'number_int'        , "sum": True   },
    {"size": 12,  "name": 'Trưởng (phó) phòng'      , 'field':"department_manager_amount" , "type": 'number_int'        , "sum": True   },
]

# Định nghĩa cột cho bảng 3: Hoa hồng TKV Thưởng xây dựng đội nhóm đạt KPI doanh số
TABLE3_COLUMNS = [
    {"size":  5,  "name": 'STT'                     , 'field':"no"                        , "type": 'number_c_int'      , "sum": False  },
    {"size": 27,  "name": 'Khu vực'                 , 'field':"region_name"               , "type": 'text'              , "sum": False  },
    {"size": 12,  "name": 'Số nhân viên đạt điều kiện', 'field':"qualified_lines_count"   , "type": 'number_c_int'      , "sum": True   },
    {"size": 12,  "name": 'Số tiền đạt được'        , 'field':"bonus_amount"              , "type": 'number_int'        , "sum": True   },
]

# Định nghĩa cột cho bảng 4: Hoa hồng khu vực (từ salary.sales.commission)
TABLE4_COLUMNS = [
    {"size":  5,  "name": 'STT'                     , 'field':"no"                        , "type": 'number_c_int'      , "sum": False  },
    {"size": 27,  "name": 'Khu vực'                 , 'field':"region_name"               , "type": 'text'              , "sum": False  },
    {"size": 12,  "name": 'Doanh thu'               , 'field':"total_revenue"             , "type": 'number_int'        , "sum": True   },
    {"size": 12,  "name": 'Thu tiền'                , 'field':"total_payment_received"    , "type": 'number_int'        , "sum": True   },
    {"size": 12,  "name": 'Tỷ lệ hoàn thành'        , 'field':"achievement_rate"          , "type": 'number_float2'     , "sum": False  },
    {"size": 12,  "name": 'Tỷ lệ thanh toán'        , 'field':"revenue_ratio"             , "type": 'number_float2'     , "sum": False  },
    {"size": 12,  "name": 'Thưởng'                  , 'field':"commission_amount"         , "type": 'number_int'        , "sum": True   },
    {"size": 12,  "name": 'Trạng thái'              , 'field':"status"                    , "type": 'text_center'       , "sum": False  },
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
        "table_title": format_workbook(workbook, 13, bold=True, align="left"),

        # Company
        "company_name": format_workbook(workbook, 13, align="left"),

        # Table Header
        "header": format_workbook(workbook, 11, bold=True, border=1, text_wrap=True, align='center'),

        # Body Text
        "text": format_workbook(workbook, 11.5, border=1, align='left', text_wrap=True),
        "text_center": format_workbook(workbook, 11.5, border=1, align='center', text_wrap=True),
        "date": format_workbook(workbook, 11.5, border=1, num_format='dd/mm/yyyy', align='center', text_wrap=True),
        "datetime": format_workbook(workbook, 11.5, border=1, num_format='dd/mm/yyyy hh:mm:ss', align='center', text_wrap=True),

        # Numbers
        "number_int": format_workbook(workbook, 10, border=1, align='right', num_format="#,##0"),
        "number_int_bold": format_workbook(workbook, 10, border=1, bold=True, align='right', num_format="#,##0"),
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


class RpSalesBonusByRegionReport(models.AbstractModel):
    _name = "report.biz_kpi_business_salary.rp_sales_bonus_by_region"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE
    
    def _init_sum(self, columns):
        """Khởi tạo dictionary để tính tổng dựa trên cấu hình COLUMNS."""
        return {col['field']: 0 for col in columns if col.get('sum')}
    
    def _get_table1_data(self, obj):
        """Lấy dữ liệu cho bảng 1: Thưởng bán hàng theo doanh số của các Khu vực"""
        employee_commissions = obj.employee_commission_ids.sorted('team_id')
        data = []
        stt = 0
        
        for commission in employee_commissions:
            stt += 1
            data.append({
                "no": stt,
                "region_name": commission.team_id.report_name if commission.team_id else '',
                "team_commission": commission.team_commission or 0,
                "leadership_commission": commission.leadership_commission or 0,
                "department_commission": commission.department_commission or 0,
                "total_commission": commission.team_commission + commission.leadership_commission + commission.department_commission or 0,
            })
        
        # Tính tổng
        totals = self._init_sum(TABLE1_COLUMNS)
        for row in data:
            for key in totals.keys():
                totals[key] += row.get(key, 0)
        
        return {
            "data": data,
            "totals": totals
        }
    
    def _get_table2_data(self, obj):
        """Lấy dữ liệu cho bảng 2: Tiền thưởng theo doanh số"""
        personnel_commissions = obj.personnel_commission_ids.sorted('team_id')
        data = []
        stt = 0
        
        for commission in personnel_commissions:
            stt += 1
            data.append({
                "no": stt,
                "region_name": commission.team_id.report_name if commission.team_id else '',
                "team_commission_amount": commission.team_commission_amount or 0,
                "sale_support_amount": commission.sale_support_amount or 0,
                "team_leader_amount": commission.team_leader_amount or 0,
                "department_manager_amount": commission.department_manager_amount or 0,
            })
        
        # Tính tổng
        totals = self._init_sum(TABLE2_COLUMNS)
        for row in data:
            for key in totals.keys():
                totals[key] += row.get(key, 0)
        
        return {
            "data": data,
            "totals": totals
        }
    
    def _get_table3_data(self, obj):
        """Lấy dữ liệu cho bảng 3: Hoa hồng TKV Thưởng xây dựng đội nhóm đạt KPI doanh số"""
        bonus_commissions = obj.bonus_commission_ids.sorted('team_id')
        data = []
        stt = 0
        
        for commission in bonus_commissions:
            stt += 1
            data.append({
                "no": stt,
                "region_name": commission.team_id.report_name if commission.team_id else '',
                "qualified_lines_count": commission.qualified_lines_count or 0,
                "bonus_amount": commission.bonus_amount or 0,
            })
        
        # Tính tổng
        totals = self._init_sum(TABLE3_COLUMNS)
        for row in data:
            for key in totals.keys():
                totals[key] += row.get(key, 0)
        
        return {
            "data": data,
            "totals": totals
        }
    
    def _get_table4_data(self, obj):
        """Lấy dữ liệu cho bảng 4: Hoa hồng khu vực (từ salary.sales.commission)"""
        sales_commissions = obj.commission_ids.sorted('team_id')
        data = []
        stt = 0
        
        status_map = {
            'achieved': 'Đạt',
            'not_achieved': 'Không đạt'
        }
        
        for commission in sales_commissions:
            stt += 1
            # Chuyển đổi achievement_rate và revenue_ratio từ dạng 0-1 sang phần trăm
            achievement_rate_percent = (commission.achievement_rate or 0) * 100
            revenue_ratio_percent = (commission.revenue_ratio or 0) * 100
            
            data.append({
                "no": stt,
                "region_name": commission.team_id.report_name if commission.team_id else '',
                "total_revenue": commission.total_revenue or 0,
                "total_payment_received": commission.total_payment_received or 0,
                "achievement_rate": achievement_rate_percent,
                "revenue_ratio": revenue_ratio_percent,
                "commission_amount": commission.commission_amount or 0,
                "status": status_map.get(commission.status, commission.status or ''),
            })
        
        # Tính tổng
        totals = self._init_sum(TABLE4_COLUMNS)
        for row in data:
            for key in totals.keys():
                totals[key] += row.get(key, 0)
        
        return {
            "data": data,
            "totals": totals
        }

    def add_title(self, sheet, formats, obj):
        # Keep company name and address fixed
        sheet.merge_range("C2:F2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751",formats["company_name"],)
        sheet.merge_range("C3:F3", "23 Lô B, Đường số 1, P. Phú Thuận, Q.7", formats["company_name"])
        
        # Keep image insertion as is
        sheet.insert_image("A1",get_module_resource("ccv_bao_cao", "static/src/img", "logo.png"),{"x_offset": 0, "y_offset": 0, "x_scale": 0.22, "y_scale": 0.22},)

        # Main title
        title_text = TITLE.upper()
        sheet.merge_range("A4:H4", title_text, formats["title_main"])
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
            sheet.merge_range("A5:H5", period_text, formats["title_sub"])
            sheet.set_row(4, 25)

    def add_table_header(self, sheet, formats, columns, start_row, start_col=0):
        """Thêm header cho bảng"""
        col = start_col
        for column in columns:
            sheet.set_column(col, col, column.get('size', 10))
            sheet.write(start_row, col, column.get('name', ''), formats["header"])
            col += 1
        return start_row + 1

    def add_table_body(self, sheet, formats, columns, data, totals, start_row):
        """Thêm body và tổng cho bảng"""
        current_row = start_row
        
        # Ghi dữ liệu
        for row_data in data:
            col = 0
            for column in columns:
                fmt = formats[column.get('type', 'text')]
                field_name = column.get('field')
                cell_value = row_data.get(field_name, '')
                
                # Xử lý đặc biệt cho kiểu ngày/thời gian
                if column.get('type') == 'date' and isinstance(cell_value, datetime):
                    cell_value = cell_value.date()
                elif column.get('type') == 'datetime' and isinstance(cell_value, datetime):
                    pass
                
                sheet.write(current_row, col, cell_value, fmt)
                col += 1
            current_row += 1
        
        # Ghi dòng tổng
        # Tìm chỉ số cột đầu tiên có 'sum': True
        first_summable_col_idx = -1
        for idx, col_def in enumerate(columns):
            if col_def.get('sum'):
                first_summable_col_idx = idx
                break
        
        merge_label_col_end_idx = max(0, first_summable_col_idx - 1) if first_summable_col_idx != -1 else len(columns) - 1
        
        # Nhãn "TỔNG CỘNG"
        sheet.merge_range(current_row, 0, current_row, merge_label_col_end_idx, 
                          "TỔNG CỘNG", formats["total_text_bold"])
        
        # Ghi tổng của từng cột summable
        for col_idx, column_def in enumerate(columns):
            if column_def.get('sum'):
                field_name = column_def.get('field')
                sum_value = totals.get(field_name, 0)
                
                # Xác định định dạng tổng phù hợp
                total_fmt_key = column_def['type'].replace('number', 'total')
                fmt = formats.get(total_fmt_key, formats["total_int"])
                
                sheet.write(current_row, col_idx, sum_value, fmt)
            elif col_idx > merge_label_col_end_idx:
                sheet.write(current_row, col_idx, "", formats["text"])
        
        # Đặt height = 30 cho dòng tổng cộng
        sheet.set_row(current_row)
        
        return current_row + 2  # Trả về dòng tiếp theo (cách 1 dòng)

    def add_table1(self, sheet, formats, obj, start_row):
        """Thêm bảng 2: Thưởng bán hàng theo doanh số của các Khu vực"""
        # Tiêu đề bảng
        sheet.write(start_row, 0, "2. Thưởng bán hàng theo doanh số của các Khu vực", formats["table_title"])
        start_row += 2
        
        # Lấy dữ liệu
        table_data = self._get_table1_data(obj)
        
        # Header
        start_row = self.add_table_header(sheet, formats, TABLE1_COLUMNS, start_row)
        
        # Body và tổng
        start_row = self.add_table_body(sheet, formats, TABLE1_COLUMNS, table_data["data"], table_data["totals"], start_row)
        
        return start_row

    def add_table2(self, sheet, formats, obj, start_row):
        """Thêm bảng 3: Tiền thưởng theo doanh số"""
        # Tiêu đề bảng
        sheet.write(start_row, 0, "3. Tiền thưởng theo doanh số", formats["table_title"])
        start_row += 2
        
        # Lấy dữ liệu
        table_data = self._get_table2_data(obj)
        
        # Header
        start_row = self.add_table_header(sheet, formats, TABLE2_COLUMNS, start_row)
        
        # Body và tổng
        start_row = self.add_table_body(sheet, formats, TABLE2_COLUMNS, table_data["data"], table_data["totals"], start_row)
        
        return start_row

    def add_table3(self, sheet, formats, obj, start_row):
        """Thêm bảng 4: Hoa hồng TKV Thưởng xây dựng đội nhóm đạt KPI doanh số"""
        # Tiêu đề bảng
        sheet.write(start_row, 0, "4. Hoa hồng TKV Thưởng xây dựng đội nhóm đạt KPI doanh số", formats["table_title"])
        start_row += 2
        
        # Lấy dữ liệu
        table_data = self._get_table3_data(obj)
        
        # Header
        start_row = self.add_table_header(sheet, formats, TABLE3_COLUMNS, start_row)
        
        # Body và tổng
        start_row = self.add_table_body(sheet, formats, TABLE3_COLUMNS, table_data["data"], table_data["totals"], start_row)
        
        return start_row

    def add_table4(self, sheet, formats, obj, start_row):
        """Thêm bảng 1: Hoa hồng khu vực (từ salary.sales.commission)"""
        # Tiêu đề bảng
        sheet.write(start_row, 0, "1. Hoa hồng khu vực", formats["table_title"])
        start_row += 2
        
        # Lấy dữ liệu
        table_data = self._get_table4_data(obj)
        
        # Header
        start_row = self.add_table_header(sheet, formats, TABLE4_COLUMNS, start_row)
        
        # Body và tổng
        start_row = self.add_table_body(sheet, formats, TABLE4_COLUMNS, table_data["data"], table_data["totals"], start_row)
        
        return start_row

    def add_signatures(self, sheet, formats, obj):
        row = sheet.dim_rowmax + 3

        # Tính toán vị trí chữ ký
        total_columns = max(len(TABLE1_COLUMNS), len(TABLE2_COLUMNS), len(TABLE3_COLUMNS), len(TABLE4_COLUMNS))
        last_column_index = total_columns - 1

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
        
        # Người ký đầu và cuối: 2 cột, 2 người còn lại: 1 cột mỗi người
        def get_block_width(i, total_blocks):
            if i == 0 or i == total_blocks - 1:  # Đầu và cuối
                return 2
            else:  # Các người ở giữa
                return 2

        current_col_idx = 0
        for i, block in enumerate(signature_blocks):
            col_start_idx = current_col_idx
            block_width = get_block_width(i, num_signature_blocks)
            
            if i == num_signature_blocks - 1:  # Người cuối cùng
                col_end_idx = last_column_index
            else:
                col_end_idx = col_start_idx + block_width - 1

            # Nếu chỉ 1 cột thì dùng write, nếu nhiều cột thì dùng merge_range
            if col_start_idx == col_end_idx:
                sheet.write(row - 1, col_start_idx, block["role"], formats["signature_name"])
            else:
                col_from_letter = chr(65 + col_start_idx)
                col_to_letter = chr(65 + col_end_idx)
                sheet.merge_range(f"{col_from_letter}{row}:{col_to_letter}{row}", block["role"], formats["signature_name"])

            current_col_idx = col_end_idx + 1
            
        row += 5 

        current_col_idx = 0
        for i, block in enumerate(signature_blocks):
            col_start_idx = current_col_idx
            block_width = get_block_width(i, num_signature_blocks)
            
            if i == num_signature_blocks - 1:  # Người cuối cùng
                col_end_idx = last_column_index
            else:
                col_end_idx = col_start_idx + block_width - 1

            # Nếu chỉ 1 cột thì dùng write, nếu nhiều cột thì dùng merge_range
            if col_start_idx == col_end_idx:
                sheet.write(row - 1, col_start_idx, block["signer"], formats["signature_name"])
            else:
                col_from_letter = chr(65 + col_start_idx)
                col_to_letter = chr(65 + col_end_idx)
                sheet.merge_range(f"{col_from_letter}{row}:{col_to_letter}{row}", block["signer"], formats["signature_name"])

            current_col_idx = col_end_idx + 1

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, obj, objects):
        for obj in objects:
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({
                "title": TITLE,
                "author": self.env.user.name_without_position if hasattr(self.env.user, 'name_without_position') else self.env.user.name,
            })
            sheet.set_landscape()
            formats = create_formats(workbook)
            
            # Thêm tiêu đề
            self.add_title(sheet, formats, obj)
            
            # Bắt đầu từ dòng 7 (sau tiêu đề)
            start_row = 5 if obj.month and obj.year else 4
            if obj.month and obj.year:
                start_row = 6
            
            # Thêm 4 bảng (bảng 4 trước bảng 1)
            start_row = self.add_table4(sheet, formats, obj, start_row)
            start_row = self.add_table1(sheet, formats, obj, start_row)
            start_row = self.add_table2(sheet, formats, obj, start_row)
            start_row = self.add_table3(sheet, formats, obj, start_row)
            
            # Thêm chữ ký
            self.add_signatures(sheet, formats, obj)

