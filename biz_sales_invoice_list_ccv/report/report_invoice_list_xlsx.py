# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime
import re
import logging

_logger = logging.getLogger(__name__)

TITLE = 'BẢNG KÊ HÓA ĐƠN, CHỨNG TỪ HÀNG HÓA, DỊCH VỤ BÁN RA'

# Định nghĩa các cột cho báo cáo
COLUMNS = [
    {"size": 16, "name": 'Ký hiệu mẫu HĐ', "field": "kyhieumau_hd", "type": 'text', "sum": False},
    {"size": 16, "name": 'Ký hiệu HĐ', "field": "kyhieu_hd", "type": 'text_center', "sum": False},
    {"size": 18, "name": 'Số hoá đơn', "field": "so_hoa_don", "type": 'text_center', "sum": False},
    {"size": 14, "name": 'Ngày hoá đơn', "field": "ngay_hoa_don", "type": 'text_center', "sum": False},
    {"size": 16, "name": 'Số chứng từ', "field": "so_chung_tu", "type": 'text_center', "sum": False},
    {"size": 27, "name": 'Tên người mua', "field": "ten_nguoi_mua", "type": 'text', "sum": False},
    {"size": 25, "name": 'Mã số thuế người mua', "field": "mst_nguoi_mua", "type": 'text_center', "sum": False},
    {"size": 40, "name": 'Mặt hàng', "field": "mat_hang", "type": 'text', "sum": False},
    {"size": 20, "name": 'Doanh số bán chưa có thuế GTGT', "field": "dsbcc_thue_gtgt", "type": 'number_int', "sum": True},
    {"size": 10, "name": 'Thuế suất', "field": "thue_suat", "type": 'text', "sum": False},
    {"size": 15, "name": 'Thuế GTGT', "field": "thue_gtgt", "type": 'number_int', "sum": True},
    {"size": 10, "name": 'TK thuế', "field": "tk_thue", "type": 'text', "sum": False},
]

type_vat_name = {
    'no_vat': '1. Hàng hóa, dịch vụ không chịu thuế giá trị gia tăng (GTGT):',
    '0_vat': '2. Hàng hóa, dịch vụ chịu thuế suất thuế GTGT 0%:',
    '5_vat': '3. Hàng hóa, dịch vụ chịu thuế suất thuế GTGT 5%:',
    '8_vat': '4. Hàng hóa, dịch vụ chịu thuế suất thuế GTGT 8%:',
    '10_vat': '5. Hàng hóa, dịch vụ chịu thuế suất thuế GTGT 10%:',
    'no_tax': '6. Hàng hóa, dịch vụ bán ra không tính thuế:'
}


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
        # Title
        "title_main": format_workbook(workbook, 16, bold=True, align="center", bg_color='#f7f700', border=1, valign='vcenter'),
        "title_sub": format_workbook(workbook, 12, bold=True, align="center", valign='vcenter'),

        # Table Header
        "header": format_workbook(workbook, 12, bold=True, border=1, text_wrap=True, align='center', bg_color='#f7ad00', valign='vcenter'),

        # Body
        "text": format_workbook(workbook, 12, border=1, align='left', text_wrap=True, valign='vcenter'),
        "text_center": format_workbook(workbook, 12, border=1, align='center', text_wrap=True, valign='vcenter'),
        "text_bold": format_workbook(workbook, 12, border=1, align='left', bold=True, text_wrap=True, valign='vcenter'),

        # Numbers
        "number_int": format_workbook(workbook, 12, border=1, align='right', num_format="#,##0", text_wrap=True, valign='vcenter'),

        # Totals
        "total_int": format_workbook(workbook, 12, border=1, bold=True, align='right', num_format="#,##0", bg_color='#F6DB36', text_wrap=True, valign='vcenter'),

        # Footer notes
        "footer_note": format_workbook(workbook, 12, border=1, bg_color='yellow', bold=True, align='center', text_wrap=True, valign='vcenter'),
    }


def get_column_letter(col_num):
    """Convert column number to Excel column letter (1=A, 2=B, etc.)"""
    result = ""
    while col_num > 0:
        col_num -= 1
        result = chr(65 + col_num % 26) + result
        col_num //= 26
    return result


class report_invoice_list_xlsx(models.AbstractModel):
    _name = 'report.biz_sales_invoice_list_ccv.report_invoice_list_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'report_invoice_list_xlsx'

    def _get_tax_type(self, line):
        """Xác định tax_type từ line"""
        if not line.tax_id:
            # Kiểm tra no_tax: không có tax và product không phải not_taxable
            if line.product_id and not line.product_id.product_not_taxable:
                return 'no_tax'
            # Kiểm tra no_vat
            if (line.product_id and line.product_id.product_not_taxable) or \
               (hasattr(line, 'aml_id') and line.aml_id and line.aml_id.tax_ids and 
                any(tax.not_taxable for tax in line.aml_id.tax_ids)):
                return 'no_vat'
            return 'no_vat'
        
        # Lấy type_vat từ tax_id
        if line.tax_id.type_vat:
            return line.tax_id.type_vat
        
        # Nếu tax_id có nhưng không có type_vat, kiểm tra not_taxable
        if hasattr(line.tax_id, 'not_taxable') and line.tax_id.not_taxable:
            return 'no_vat'
        
        return 'no_vat'

    def _get_data_export(self, obj, type_vat):
        """Lấy dữ liệu và group theo move_id để aggregate"""
        obj = obj.with_context(lang=obj.env.user.lang)
        
        # Lọc lines theo tax_type và is_not_uploaded (nếu có field này)
        
        result = []
        sum_dt = 0
        sum_thue = 0
        
        # Lọc lines theo tax_type
        lines = obj.line_ids.filtered(lambda line: self._get_tax_type(line) == type_vat)
        
        # Group by invoice unique info to aggregate data
        # Bộ phím: (invoice_code_key, invoice_code, invoice_number, invoice_date, buyer_id)
        groups = {}
        for line in lines:
            key = (line.invoice_code_key or '', line.invoice_code or '', line.invoice_number or '', line.invoice_date or False, line.buyer_id.id or False)
            if key not in groups:
                groups[key] = obj.env['sale.invoices.list.line.ccv']
            groups[key] |= line

        for key, move_lines in groups.items():
            invoice_code_key, invoice_code, invoice_number, invoice_date, buyer_id = key
            
            mat_hang = ', '.join([name for name in move_lines.mapped('name') if name])
            
            # Calculate totals
            doanhthu = sum(move_lines.mapped('base_amount'))
            thue = sum(move_lines.mapped('tax_amount'))
            thue_suat = move_lines[0].tax_id.amount if move_lines[0].tax_id else 0
            tk_thue_code = ','.join(set(move_lines.mapped('tax_account_id.code')).difference([None, False]))
            
            sum_dt += doanhthu
            sum_thue += thue
            
            result.append({
                'kyhieumau_hd': invoice_code_key,
                'kyhieu_hd': invoice_code,
                'so_hoa_don': invoice_number,
                'ngay_hoa_don': invoice_date.strftime('%d/%m/%Y') if invoice_date else '',
                'so_chung_tu': move_lines[0].ref or '',
                'ten_nguoi_mua': move_lines[0].buyer_id.name or '',
                'mst_nguoi_mua': move_lines[0].buyer_tax or '',
                'mat_hang': mat_hang,
                'dsbcc_thue_gtgt': doanhthu,
                'thue_suat': thue_suat,
                'thue_gtgt': thue,
                'tk_thue': tk_thue_code or '',
                'type': 'line'
            })
        
        # Sort by date, invoice template, invoice series, invoice number
        def parse_date(date_str):
            if not date_str or not isinstance(date_str, str):
                return datetime.min
            try:
                return datetime.strptime(date_str, '%d/%m/%Y')
            except (ValueError, TypeError):
                return datetime.min
        
        def sort_key(item):
            item_type = item.get('type', '')
            if item_type != 'line':
                return (datetime.max, '', '', '')
            ngay_hoa_don = item.get('ngay_hoa_don', '') or ''
            kyhieumau_hd = str(item.get('kyhieumau_hd', '') or '')
            kyhieu_hd = str(item.get('kyhieu_hd', '') or '')
            so_hoa_don = str(item.get('so_hoa_don', '') or '')
            return (parse_date(ngay_hoa_don), kyhieumau_hd, kyhieu_hd, so_hoa_don)
        
        result = sorted(result, key=sort_key)
        
        # Add total row (sẽ được thêm ở cuối sau khi sort)
        val_thue = sum_thue if type_vat in ['no_vat', '0_vat', '5_vat', '8_vat', '10_vat'] else ''
        total_row = {
            'kyhieumau_hd': '',
            'kyhieu_hd': '',
            'so_hoa_don': '',
            'ngay_hoa_don': '',
            'so_chung_tu': '',
            'ten_nguoi_mua': '',
            'mst_nguoi_mua': '',
            'mat_hang': '',
            'dsbcc_thue_gtgt': sum_dt if sum_dt != 0 else 0,
            'thue_suat': '',
            'thue_gtgt': val_thue if val_thue != '' and val_thue != 0 else 0,
            'type': 'total',
        }
        
        # Thêm total row vào cuối (sau data lines)
        result.append(total_row)
        
        return result

    def add_title(self, sheet, formats, obj, start_row):
        # Main title
        last_column_letter = get_column_letter(len(COLUMNS))
        title_text = TITLE
        sheet.merge_range(f"A{start_row + 1}:{last_column_letter}{start_row + 1}", title_text, formats["title_main"])
        sheet.set_row(start_row, 30)
        start_row += 1
        
        # Month and year
        month_text = ''
        if obj.from_date:
            month = obj.from_date.strftime('%m/%Y').split('/')[0]
            year = obj.from_date.strftime('%m/%Y').split('/')[1]
            month_text = f'Tháng {month} năm {year}'
        
        if month_text:
            sheet.merge_range(f"A{start_row + 1}:{last_column_letter}{start_row + 1}", month_text, formats["title_sub"])
            sheet.set_row(start_row, 30)
            start_row += 1
        return start_row

    def add_header(self, sheet, formats, obj, start_row):
        # Header row 1: Column names
        row1 = start_row
        # Header row 2: Same row (merged)
        row2 = start_row + 1
        
        col = 0
        for column in COLUMNS:
            name = column.get("name", "")
            # Merge 2 rows cho mỗi cột
            sheet.merge_range(row1, col, row2, col, name, formats["header"])
            col += 1
        
        return row2 + 1

    def add_body(self, sheet, formats, obj, start_row):
        # Set column widths
        for col_idx, column_def in enumerate(COLUMNS):
            sheet.set_column(col_idx, col_idx, column_def.get('size', 10))
        
        # Process each type_vat
        for type_vat in ['no_vat', '0_vat', '5_vat', '8_vat', '10_vat']:
            lines_data = self._get_data_export(obj, type_vat)
            
            # Tách các loại dòng
            data_lines = [line for line in lines_data if line.get('type') == 'line']
            total_line = next((line for line in lines_data if line.get('type') == 'total'), None)
            
            # Write section title
            sheet.merge_range(start_row, 0, start_row, len(COLUMNS) - 1, 
                            type_vat_name[type_vat], formats["text_bold"])
            start_row += 1
            
            # Write data lines first
            for line_data in data_lines:
                for col_idx, column_def in enumerate(COLUMNS):
                    field_name = column_def.get('field')
                    cell_value = line_data.get(field_name, '')
                    
                    # Xác định format
                    if column_def.get('type') == 'number_int':
                        fmt = formats["number_int"]
                    else:
                        fmt = formats["text"]
                    
                    sheet.write(start_row, col_idx, cell_value, fmt)
                start_row += 1
            
            # Write total row ở dưới (if exists)
            if total_line:
                for col_idx, column_def in enumerate(COLUMNS):
                    field_name = column_def.get('field')
                    cell_value = total_line.get(field_name, '')
                    
                    # Xác định format
                    if column_def.get('sum'):
                        fmt = formats["total_int"]
                    else:
                        fmt = formats["text_center"]
                    
                    sheet.write(start_row, col_idx, cell_value, fmt)
                start_row += 1
        return start_row

    def add_footer_notes(self, sheet, formats, obj, start_row):
        # Footer notes
        notes = [
            'Kê khai các hóa đơn đầu ra đã xuất bán HH-DV trong kỳ',
            'Không kê khai các hóa đơn của các kỳ khác',
            'Không kê khai các hóa đơn xóa bỏ (HĐ viết sai)',
        ]
        
        for note in notes:
            sheet.merge_range(f"B{start_row + 1}:G{start_row + 1}", note, formats["footer_note"])
            start_row += 1
        return start_row

    def generate_xlsx_report(self, workbook, data, objects):
        self = self.with_context(lang=self.env.user.lang)
        
        for obj in objects.sudo():
            sheet = workbook.add_worksheet("BẢNG KÊ HÓA ĐƠN HHDV BÁN RA")
            author_name = getattr(self.env.user, 'name_without_position', None) or self.env.user.name
            workbook.set_properties({
                "title": TITLE,
                "author": author_name,
            })
            sheet.set_margins(0.25, 0.25, 0.25, 0.75)
            
            # Set column widths
            for col_idx, column_def in enumerate(COLUMNS):
                sheet.set_column(col_idx, col_idx, column_def.get('size', 10))
            
            formats = create_formats(workbook)
            curr_row = 0
            curr_row = self.add_title(sheet, formats, obj, curr_row)
            curr_row = self.add_header(sheet, formats, obj, curr_row)
            curr_row = self.add_body(sheet, formats, obj, curr_row)
            curr_row = self.add_footer_notes(sheet, formats, obj, curr_row)
