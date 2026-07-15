# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError
from datetime import datetime
import base64
import io
import re
import html2text
from bs4 import BeautifulSoup
from datetime import timedelta
import xlsxwriter
import ast
import json
import logging

_logger = logging.getLogger(__name__)
TITLE = 'Sổ chi tiết bán hàng theo khách hàng'

COLUMNS = [
    {'size': 5,  'name': 'STT'                    , 'field': 'stt'                    , 'type': 'number_c_int'       , 'sum': False},
    {'size': 12, 'name': 'Số chứng từ'            , 'field': 'name'                   , 'type': 'text'               , 'sum': False},
    {'size': 7.86, 'name': 'Số hoá đơn'             , 'field': 'vat_sinvoice_number'    , 'type': 'text'               , 'sum': False},
    {'size': 10, 'name': 'Ngày hoá đơn'           , 'field': 'vat_sinvoice_date'      , 'type': 'date'               , 'sum': False},
    {'size': 10, 'name': 'Ngày chứng từ'          , 'field': 'date'                   , 'type': 'date'               , 'sum': False},
    {'size': 15, 'name': 'Diễn giải chung'        , 'field': 'stock_sale_export'      , 'type': 'text'               , 'sum': False},
    {'size': 15, 'name': 'Mã khách hàng'          , 'field': 'code_contact'           , 'type': 'text'               , 'sum': False},
    {'size': 15, 'name': 'Tên khách hàng'         , 'field': 'partner_name'           , 'type': 'text'               , 'sum': False},
    {'size': 11.14, 'name': 'Mã hàng'                , 'field': 'default_code'           , 'type': 'text'               , 'sum': False},
    {'size': 15, 'name': 'Tên hàng'               , 'field': 'product_name'           , 'type': 'text'               , 'sum': False},
    {'size': 5, 'name': 'ĐVT'                    , 'field': 'product_uom_id'         , 'type': 'text'               , 'sum': False},
    {'size': 10, 'name': 'Tổng số lượng bán'      , 'field': 'qty_invoiced'           , 'type': 'number_float3'      , 'sum': True},
    {'size': 10, 'name': 'Đơn giá'                , 'field': 'price_unit'             , 'type': 'number_int'         , 'sum': False},
    {'size': 10, 'name': 'Doanh số chưa thuế'     , 'field': 'price_subtotal'         , 'type': 'number_int'         , 'sum': True},
    {'size': 10, 'name': 'Giá trị thuế'           , 'field': 'amount_tax'             , 'type': 'number_int'         , 'sum': True},
    {'size': 10, 'name': 'Doanh số sau thuế'      , 'field': 'price_subtotal_tax'     , 'type': 'number_int'         , 'sum': True},
    {'size': 10, 'name': 'Số lượng trả lại'       , 'field': 'qty_done'               , 'type': 'number_float3'      , 'sum': True},
    {'size': 10, 'name': 'Giá trị trả lại'        , 'field': 'price_done'             , 'type': 'number_int'         , 'sum': True},
    {'size': 12, 'name': 'Nhân viên bán hàng' , 'field': 'user_id'                , 'type': 'text'               , 'sum': False},
    {'size': 20, 'name': 'Xã/Phường'              , 'field': 'partner_ward_district'  , 'type': 'text'               , 'sum': False},
    {'size': 10, 'name': 'Tỉnh/Thành phố'         , 'field': 'order_state_id'         , 'type': 'text'               , 'sum': False},
    {'size': 10, 'name': 'Khu vực'                , 'field': 'team_id'                , 'type': 'text'               , 'sum': False},
    {'size': 10.43, 'name': 'Đơn hàng'               , 'field': 'order_id'               , 'type': 'text'               , 'sum': False},
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
        'title_main': format_workbook(workbook, 16, bold=True, align='center'),
        'title_sub': format_workbook(workbook, 12, bold=True, italic=True, text_wrap=True, align='center'),

        # Company
        'company_name': format_workbook(workbook, 13, align='left'),

        # Table Header
        'header': format_workbook(workbook, 11, bold=True, border=1, text_wrap=True, align='center'),

        # Body Text
        'text': format_workbook(workbook, 11.5, border=1, align='center', text_wrap=True),
        'date': format_workbook(workbook, 11.5, border=1, num_format='dd/mm/yyyy', align='center', text_wrap=True),
        'datetime': format_workbook(workbook, 11.5, border=1, num_format='dd/mm/yyyy hh:mm:ss', align='center', text_wrap=True),

        # Numbers
        'number_int': format_workbook(workbook, 10, border=1, align='right', num_format='#,##0'),
        'number_float2': format_workbook(workbook, 10, border=1, align='right', num_format='#,##0.00'),
        'number_float3': format_workbook(workbook, 10, border=1, align='right', num_format='#,##0.000'),
        'number_c_int': format_workbook(workbook, 10, border=1, align='center', num_format='#,##0'),
        'number_c_float2': format_workbook(workbook, 10, border=1, align='center', num_format='#,##0.00'),
        'number_c_float3': format_workbook(workbook, 10, border=1, align='center', num_format='#,##0.000'),

        # Totals
        'total_int': format_workbook(workbook, 10, border=1, bold=True, align='right', num_format='#,##0'),
        'total_float2': format_workbook(workbook, 10, border=1, bold=True, align='right', num_format='#,##0.00'),
        'total_float3': format_workbook(workbook, 10, border=1, bold=True, align='right', num_format='#,##0.000'),
        'total_c_int': format_workbook(workbook, 10, border=1, bold=True, align='center', num_format='#,##0'),
        'total_c_float2': format_workbook(workbook, 10, border=1, bold=True, align='center', num_format='#,##0.00'),
        'total_c_float3': format_workbook(workbook, 10, border=1, bold=True, align='center', num_format='#,##0.000'),
        'total_text_bold': format_workbook(workbook, 10, border=1, bold=True, text_wrap=True, align='left'),

        # Description
        'description_bold': format_workbook(workbook, 10, bold=True, text_wrap=True, align='left'),
        'description': format_workbook(workbook, 10, text_wrap=True, align='left'),

        # Signature
        'signature_name': format_workbook(workbook, 12, bold=True, align='center', text_wrap=True, valign='vcenter'),
        'signature_note': format_workbook(workbook, 12, italic=True, align='center', text_wrap=True),
        'signature_date': format_workbook(workbook, 11, italic=True, align='center', text_wrap=True),
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


class ReportDetailsSalesBookByCustomer(models.AbstractModel):
    _name = 'report.biz_details_sales_book_by_customer.details_book_xlsx'
    _description = TITLE
    _inherit = 'report.report_xlsx.abstract'
    
    def add_title(self, sheet, formats, obj):
        # Keep company name and address fixed
        company_id = self.env.company
        sheet.merge_range("C2:G2", f"{company_id.name} - Mã số thuế: {company_id.vat}", formats["company_name"])
        sheet.merge_range("C3:G3", company_id.street or "", formats["company_name"])
        
        # Keep image insertion as is
        image = company_id.logo or False
        if image:
            image_data = io.BytesIO(base64.b64decode(image))
            sheet.insert_image("A1", image, {'image_data': image_data, 'x_scale': 0.2, 'y_scale': 0.2, 'x_offset': 0, 'y_offset': 0})

        # Calculate the last column letter dynamically
        last_column_letter = chr(65 + len(COLUMNS) - 1)

        # Adjust main title to span all columns
        title_text = TITLE.upper()
        if obj.type_partner == 'team':
            team_names = ', '.join(obj.team_id.mapped(lambda t: t.report_name or t.name or ''))
            title_text = f'{title_text} - {team_names}'
        sheet.merge_range(f"A4:{last_column_letter}4", title_text, formats["title_main"])
        sheet.set_row(3, 35)

        # Add date range subtitle
        from_date = ''
        to_date = ''
        if obj.date_from:
            from_date = obj.date_from.strftime('%d/%m/%Y')
        if obj.date_to:
            to_date = obj.date_to.strftime('%d/%m/%Y')
        sub_title = f'Từ ngày {from_date} đến ngày {to_date}'
        sheet.merge_range(f"A5:{last_column_letter}5", sub_title, formats["title_sub"])

    def add_header(self, sheet, formats, obj):
        row = 6
        col = 0

        for column in COLUMNS:
            name = column.get("name", "")
            sheet.write(row, col, name, formats["header"])
            col += 1

    def add_body(self, sheet, formats, obj):
        lines = self.get_lines(obj)

        # Sort and group by team_id
        lines.sort(key=lambda x: x.get('team_id') or 'ZZZ_Không xác định')
        grouped_lines = {}
        for line in lines:
            team = line.get('team_id') or 'Không xác định'
            if team not in grouped_lines:
                grouped_lines[team] = []
            grouped_lines[team].append(line)

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

        global_stt = 1
        for team, team_lines in grouped_lines.items():
            # Ghi các dòng dữ liệu chi tiết của khu vực
            for row_data in team_lines:
                row_data['stt'] = global_stt
                global_stt += 1
                for col_idx, column_def in enumerate(COLUMNS):
                    sheet.set_column(col_idx, col_idx, column_def.get('size', 10))
                    fmt = formats[column_def.get('type', 'text')]

                    field_name = column_def.get('field')
                    cell_value = row_data.get(field_name)

                    if column_def.get('type') == 'date' and isinstance(cell_value, datetime):
                        cell_value = cell_value.date()
                    elif column_def.get('type') == 'datetime' and isinstance(cell_value, datetime):
                        pass

                    sheet.write(prod_row, col_idx, cell_value, fmt)
                prod_row += 1

            # Ghi dòng tổng cộng của khu vực
            team_totals = {
                'qty_invoiced': sum([line.get('qty_invoiced', 0) for line in team_lines]),
                'price_subtotal': sum([line.get('price_subtotal', 0) for line in team_lines]),
                'amount_tax': sum([line.get('amount_tax', 0) for line in team_lines]),
                'price_subtotal_tax': sum([line.get('price_subtotal_tax', 0) for line in team_lines]),
                'qty_done': sum([line.get('qty_done', 0) for line in team_lines]),
                'price_done': sum([line.get('price_done', 0) for line in team_lines]),
            }

            sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx,
                              f"Tổng {team}", formats["total_text_bold"])

            for col_idx, column_def in enumerate(COLUMNS):
                if column_def['sum']:
                    field_name = column_def.get('field', '')
                    sum_value = team_totals.get(field_name, 0)
                    total_fmt_key = column_def['type'].replace('number', 'total')
                    fmt = formats.get(total_fmt_key, formats["total_int"])
                    sheet.write(prod_row, col_idx, sum_value, fmt)
                elif col_idx > merge_label_col_end_idx:
                    sheet.write(prod_row, col_idx, "", formats["text"])
            prod_row += 1

        # Ghi dòng tổng cộng chung
        totals = {
            'qty_invoiced': sum([line.get('qty_invoiced', 0) for line in lines]),
            'price_subtotal': sum([line.get('price_subtotal', 0) for line in lines]),
            'amount_tax': sum([line.get('amount_tax', 0) for line in lines]),
            'price_subtotal_tax': sum([line.get('price_subtotal_tax', 0) for line in lines]),
            'qty_done': sum([line.get('qty_done', 0) for line in lines]),
            'price_done': sum([line.get('price_done', 0) for line in lines]),
        }

        sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                          "TỔNG CỘNG", formats["total_text_bold"])

        for col_idx, column_def in enumerate(COLUMNS):
            if column_def['sum']:
                field_name = column_def.get('field', '')
                sum_value = totals.get(field_name, 0)

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
            {"role": "Người lập biểu", "signer": obj.creator_id.name_without_position if obj.creator_id else ""},
            {"role": "Thống kê BĐH", "signer": obj.statistics_id.name_without_position if obj.statistics_id else ""},
            {"role": "Kế toán công nợ", "signer": obj.account_liability_id.name_without_position if obj.account_liability_id else ""},
            {"role": "Kế toán trưởng", "signer": obj.accountant_chief_id.name_without_position if obj.accountant_chief_id else ""},
            {"role": "Thủ trưởng đơn vị", "signer": obj.unit_head_id.name_without_position if obj.unit_head_id else ""},
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

    def generate_xlsx_report(self, workbook: xlsxwriter.Workbook, data, details):
        self = self.with_context(lang=self.env.user.lang)
        for obj in details:
            worksheet_name = _("Report details sales book by customer")
            sheet = workbook.add_worksheet(worksheet_name)
            workbook.set_properties({"title": TITLE, "author": self.env.user.name_without_position})
            sheet.set_landscape()
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)

    def get_lines(self,o):
        result = []
        stt = 0
        for line in o.line_ids:
            stt += 1
            result.append({
                'stt': stt,
                'name': line.reference or '',
                'date': line.date or '',
                'vat_sinvoice_number': line.vat_sinvoice_number or '',
                'vat_sinvoice_date': line.vat_sinvoice_date or '',
                'stock_sale_export': line.stock_sale_export or '',
                'code_contact': line.partner_id and line.partner_id.code_contact or '',
                'default_code': line.product_id and line.product_id.default_code or '',
                'product_name': line.product_id and line.product_id.name or '',
                'partner_name': line.partner_id and line.partner_id.name or '',
                'product_uom_id': line.product_uom and line.product_uom.name.upper() or '',
                'qty_invoiced': line.qty_invoiced,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'amount_tax': line.amount_tax,
                'price_subtotal_tax': line.price_subtotal_tax,
                'qty_done': line.qty_done,
                'price_done': line.price_done,
                'user_id': line.user_id.name_without_position or '',
                'partner_ward_district': line.partner_ward_district or '',
                'order_state_id': line.order_state_id.name or '',
                'team_id': line.team_id.name or '',
                'order_id': line.order_id.name or '',
            })
        return result
    
    def format_float_number(self, num,f_covert=False):
        if not num:
            return 0
        number = float(num)
        if f_covert:
            return "{:,.3f}".format(number)

        if number % 1 == 0:
            return "{:,.0f}".format(number)
        else:
            number_format = "{:,.2f}".format(number).rstrip('0')
            return number_format
    
    def get_reason_output_input_stock(self, reason_output_input_stock):
        if reason_output_input_stock:
            # soup = BeautifulSoup(reason_output_input_stock, 'html.parser')
            # return soup.get_text()
            soup = BeautifulSoup(reason_output_input_stock, 'lxml')
            soup_format = soup.prettify()
            html2_text = html2text.html2text(soup_format)
            clean_note = re.sub(r'[^\w\s,\-]', '', html2_text)
            clean_note = '\n'.join([line.strip() for line in clean_note.splitlines() if line.strip()])
            return clean_note.strip()
        return ''