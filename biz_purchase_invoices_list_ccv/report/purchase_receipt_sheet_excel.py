# -*- coding: utf-8 -*-
from datetime import datetime, date as date_type
from odoo import models
from odoo.modules.module import get_module_resource
from collections import defaultdict
import logging
import re
import xlsxwriter

_logger = logging.getLogger(__name__)
TITLE = 'BẢNG KÊ HÓA ĐƠN, CHỨNG TỪ HÀNG HÓA, DỊCH VỤ MUA VÀO'

# Định nghĩa các cột cho báo cáo
COLUMNS = [
    {"size": 18, "name": 'Ký hiệu mẫu HĐ',                     'field': "invoice_code_key",  "type": 'text',            "sum": False},
    {"size": 18, "name": 'Ký hiệu HĐ',                         'field': "invoice_code",      "type": 'text',            "sum": False},
    {"size": 20, "name": 'Số hoá đơn',                         'field': "invoice_number",    "type": 'text',            "sum": False},
    {"size": 18, "name": 'Ngày hoá đơn',                       'field': "invoice_date",      "type": 'date',            "sum": False},
    {"size": 18, "name": 'Ngày chứng từ',                      'field': "date",              "type": 'date',            "sum": False},
    {"size": 25, "name": 'Số chứng từ',                        'field': "ref",               "type": 'text',            "sum": False},
    {"size": 30, "name": 'Tên người bán',                      'field': "seller_id",         "type": 'text',            "sum": False},
    {"size": 24, "name": 'Mã số thuế người bán',               'field': "seller_tax",        "type": 'text',            "sum": False},
    {"size": 40, "name": 'Mặt hàng',                           'field': "product_id",        "type": 'text',            "sum": False},
    {"size": 25, "name": 'Giá trị HHDV mua vào chưa có thuế',  'field': "base_amount",       "type": 'number_int',      "sum": True},
    {"size": 12, "name": 'Thuế suất',                          'field': "tax_id",            "type": 'text',            "sum": False},
    {"size": 20, "name": 'Thuế GTGT',                          'field': "tax_amount",        "type": 'number_int',      "sum": True},
    {"size": 12, "name": 'TK thuế',                            'field': "tax_account_id",    "type": 'text',            "sum": False},
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
        "title_main": format_workbook(workbook, 20, bold=True, align="center", bg_color='yellow', font_color='red', border=1, valign='vcenter'),
        "title_sub": format_workbook(workbook, 16, bold=True, align="center", font_color='blue', border=1, valign='vcenter'),

        # Table Header
        "header": format_workbook(workbook, 13, bold=True, border=1, text_wrap=True, align='center', bg_color='#CCFFCC', valign='vcenter'),

        # Body Text
        "text": format_workbook(workbook, 13, border=1, align='center', text_wrap=True, valign='vcenter'),
        "date": format_workbook(workbook, 13, border=1, num_format='dd/mm/yyyy', align='center', text_wrap=True, valign='vcenter'),

        # Numbers
        "number_int": format_workbook(workbook, 13, border=1, align='right', num_format="#,##0", text_wrap=True, valign='vcenter'),

        # Totals
        "total_int": format_workbook(workbook, 13, border=1, bold=True, align='right', num_format="#,##0", bg_color='yellow', text_wrap=True, valign='vcenter'),
        "total_text_bold": format_workbook(workbook, 13, border=1, bold=True, text_wrap=True, align="left", bg_color='yellow', valign='vcenter'),

        # Description
        "description_bold": format_workbook(workbook, 13, bold=True, text_wrap=True, align="left", valign='vcenter'),
        "description": format_workbook(workbook, 13, text_wrap=True, align="left", valign='vcenter'),

        # Footer notes
        "footer_note": format_workbook(workbook, 13, border=1, bg_color='yellow', font_color='red', align='right', text_wrap=True, bold=True, valign='vcenter'),
    }

def get_column_letter(col_num):
    """Convert column number to Excel column letter (1=A, 2=B, etc.)"""
    result = ""
    while col_num > 0:
        col_num -= 1
        result = chr(65 + col_num % 26) + result
        col_num //= 26
    return result

class PurchaseReceipSheetXlsx(models.AbstractModel):
    _name = 'report.biz_purchase_invoices_list_ccv.purchase_ccv_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Purchase Receip Sheet Xlsx'

    def _init_sum(self):
        """Khởi tạo dictionary để tính tổng dựa trên cấu hình COLUMNS."""
        return {col['field']: 0 for col in COLUMNS if col.get('sum')}

    def _get_product_name(self, line):
        """Lấy tên sản phẩm từ line"""
        product_name = ''
        if line.product_id:
            product_name = line.product_id.name or ''
            # Check if product has product_general_vat
            if line.product_id.product_general_vat:
                product_name = line.product_id.product_general_vat.name
            # Remove prefix if starts with [
            if product_name.startswith("["):
                product_name = re.sub(r"^\[[^\]]+\]\s*", "", line.aml_id.name or product_name)
        return product_name

    def _get_data_export(self, obj):
        """Lấy dữ liệu và group theo seller_id, invoice_code_key, invoice_code, invoice_number, invoice_date, date, tax_id"""
        from datetime import date as date_type
        min_date = date_type(1900, 1, 1)
        lines = obj.line_ids.filtered(lambda l: not l.is_not_uploaded).sorted(lambda l: (
            l.seller_id.id or 0,
            l.invoice_code_key or '',
            l.invoice_code or '',
            l.invoice_number or '',
            l.invoice_date or min_date,
            l.date or min_date,
            l.tax_id.id or 0
        ))
        
        grouped = {}
        grand_totals = self._init_sum()
        
        # Group key: (seller_id, invoice_code_key, invoice_code, invoice_number, invoice_date, date, tax_id)
        for line in lines:
            # Tạo key để group
            group_key = (
                line.seller_id.id if line.seller_id else None,
                line.invoice_code_key or '',
                line.invoice_code or '',
                line.invoice_number or '',
                line.invoice_date or None,
                line.date or None,
                line.tax_id.id if line.tax_id else None,
            )
            
            if group_key not in grouped:
                # Khởi tạo group mới
                grouped[group_key] = {
                    'lines': [],
                    'product_names': set(),  # Dùng set để loại bỏ trùng lặp
                    'refs': set(),  # Dùng set để loại bỏ trùng lặp
                    'sums': self._init_sum(),
                    'first_line': line,  # Lưu line đầu tiên để lấy thông tin chung
                }
            
            # Lấy tên sản phẩm
            product_name = self._get_product_name(line)
            if product_name:
                grouped[group_key]['product_names'].add(product_name)
            
            # Lấy ref
            if line.ref:
                grouped[group_key]['refs'].add(line.ref)
            
            # Cộng vào tổng
            if line.base_amount:
                grouped[group_key]['sums']['base_amount'] += line.base_amount
                grand_totals['base_amount'] += line.base_amount
            if line.tax_amount:
                grouped[group_key]['sums']['tax_amount'] += line.tax_amount
                grand_totals['tax_amount'] += line.tax_amount
        
        # Chuyển đổi grouped thành format phù hợp với export
        export_data = []
        for group_key, group_data in grouped.items():
            seller_id, invoice_code_key, invoice_code, invoice_number, invoice_date, date, tax_id = group_key
            
            # Lấy thông tin từ line đầu tiên trong group
            first_line = group_data['first_line']
            
            # Lấy seller info
            seller_name = first_line.seller_id.name if first_line.seller_id else ''
            seller_tax = first_line.seller_tax or ''
            
            # Lấy tax info
            tax_rate = ''
            if first_line.tax_id and first_line.tax_id.amount:
                tax_rate = "{:,.2f}".format(first_line.tax_id.amount)
            
            # Lấy tax_account_id từ line
            tax_account_code = first_line.tax_account_id.code if first_line.tax_account_id else ''
            
            # Join product_id và ref bằng dấu phẩy (chuyển set thành list rồi join)
            product_names_str = ', '.join(sorted(filter(None, group_data['product_names'])))
            refs_str = ', '.join(sorted(filter(None, group_data['refs'])))
            
            line_data = {
                'invoice_code_key': invoice_code_key,
                'invoice_code': invoice_code,
                'invoice_number': invoice_number,
                'invoice_date': invoice_date,  # Giữ nguyên date object để format đúng
                'date': date,  # Giữ nguyên date object để format đúng
                'ref': refs_str,
                'seller_id': seller_name,
                'seller_tax': seller_tax,
                'product_id': product_names_str,
                'base_amount': group_data['sums']['base_amount'],
                'tax_id': tax_rate,
                'tax_amount': group_data['sums']['tax_amount'],
                'tax_account_id': tax_account_code,
            }
            export_data.append(line_data)
        
        return {
            "lines": export_data,
            "grand_totals": grand_totals
        }

    def add_title(self, sheet, formats, obj):
        global start_row
        start_row = 0
        
        # Main title
        last_column_letter = get_column_letter(len(COLUMNS))
        title_text = TITLE
        sheet.merge_range(f"A{start_row + 1}:{last_column_letter}{start_row + 1}", title_text, formats["title_main"])
        sheet.set_row(start_row, 30)
        start_row += 1
        
        # Month and year
        month_text = ''
        if obj.date_from:
            month = obj.date_from.strftime('%m/%Y').split('/')[0]
            year = obj.date_from.strftime('%m/%Y').split('/')[1]
            month_text = f'Tháng {month} năm {year}'
        
        if month_text:
            sheet.merge_range(f"A{start_row + 1}:{last_column_letter}{start_row + 1}", month_text, formats["title_sub"])
            sheet.set_row(start_row, 30)
            start_row += 1

    def add_header(self, sheet, formats, obj):
        global start_row
        
        # Header row 1: Column names
        row1 = start_row
        # Header row 2: [1], [2], [3], ...
        row2 = start_row + 1
        
        col = 0
        for i, column in enumerate(COLUMNS):
            name = column.get("name", "")
            # Merge 2 rows cho mỗi cột
            sheet.merge_range(row1, col, row2, col, name, formats["header"])
            col += 1
        
        # Write [1], [2], [3], ... ở row2
        col = 0
        for i in range(len(COLUMNS)):
            sheet.write(row2, col, f'[{i+1}]', formats["header"])
            col += 1
        
        start_row = row2 + 1

    def add_body(self, sheet, formats, obj):
        global start_row
        lines_data = self._get_data_export(obj)
        prod_row = start_row
        
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
        
        # Ghi các dòng dữ liệu
        for row_data in lines_data.get("lines", []):
            for col_idx, column_def in enumerate(COLUMNS):
                sheet.set_column(col_idx, col_idx, column_def.get('size', 10))
                fmt = formats[column_def.get('type', 'text')]
                
                field_name = column_def.get('field')
                cell_value = row_data.get(field_name)
                
                # Xử lý đặc biệt cho kiểu ngày/thời gian
                if column_def.get('type') == 'date':
                    if isinstance(cell_value, datetime):
                        cell_value = cell_value.date()
                    elif isinstance(cell_value, date_type):
                        # Đã là date object, giữ nguyên
                        pass
                    elif cell_value is None:
                        cell_value = ''
                
                sheet.write(prod_row, col_idx, cell_value, fmt)
            prod_row += 1
        
        # Ghi dòng tổng cộng
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
        start_row = prod_row + 2

    def add_footer_notes(self, sheet, formats, obj):
        global start_row
        
        last_column_letter = get_column_letter(len(COLUMNS))
        
        # Footer notes
        notes = [
            'Kê khai các HĐ GTGT đầu vào phát sinh trong kỳ',
            '(Bao gồm cả các HĐ bỏ sót của kỳ trước(nếu có) - DN được KK khấu trừ trước khi CQT công bố QĐ kiểm tra tại DN)',
            'Hóa đơn bán hàng thông thường(không phải là hóa đơn GTGT) không nên kê vào Bảng kê hóa đơn mua vào (Theo hướng dẫn tại CV 3430/TCK-KK ngày 21/08/2014)',
            'Hóa đơn đầu và là hóa đơn không chịu thuế thì cũng không kê khai vào bảng kê này theo công văn 4943/TCT-CS ngày 10/11/2014',
        ]
        
        for note in notes:
            sheet.merge_range(f"A{start_row + 1}:{last_column_letter}{start_row + 1}", note, formats["footer_note"])
            start_row += 1

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, obj, objects):
        global start_row
        for obj in objects.sudo():
            start_row = 0
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({
                "title": TITLE,
                "author": self.env.user.name_without_position if hasattr(self.env.user, 'name_without_position') else self.env.user.name,
            })
            sheet.set_landscape()
            sheet.set_margins(0.25, 0.25, 0.25, 0.75)
            
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_footer_notes(sheet, formats, obj)
