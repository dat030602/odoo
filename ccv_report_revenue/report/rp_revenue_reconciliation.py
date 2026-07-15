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
TITLE = 'Bảng kê chênh lệch doanh thu'


COLUMNS = [
    {"size":  5,                                "name": 'STT'                 , 'field':"no"                               , "type": 'number_c_int'       , "sum": False  },
    {"size": 15,                                "name": 'Khách hàng'          , 'field':"partner_name"                     , "type": 'text'               , "sum": False  },
    {"size": 12,  "group": "Sổ cái",            "name": 'Ngày hạch toán'      , 'field':"stock_date_receipt"               , "type": 'date'               , "sum": False  },
    {"size": 12,  "group": "Sổ cái",            "name": 'Ngày chứng từ'       , 'field':"stock_date_receipt"               , "type": 'date'               , "sum": False  },
    {"size": 15,  "group": "Sổ cái",            "name": 'Số chứng từ'         , 'field':"picking_name"                     , "type": 'text'               , "sum": False  },
    {"size": 15,  "group": "Sổ cái",            "name": 'Diễn giải'           , 'field':"note"                             , "type": 'text'               , "sum": False  },
    {"size": 10,  "group": "Sổ cái",            "name": 'Số tiền'             , 'field':"amount_order"                     , "type": 'number_int'         , "sum": True  },
    {"size": 12,  "group": "Bảng kê bán ra",    "name": 'Ngày hóa đơn'        , 'field':"date"                             , "type": 'date'               , "sum": False  },
    {"size": 15,  "group": "Bảng kê bán ra",    "name": 'Số hóa đơn'          , 'field':"invoice_name"                     , "type": 'text'               , "sum": False  },
    {"size": 15,  "group": "Bảng kê bán ra",    "name": 'Số chứng từ'         , 'field':"move_name"                        , "type": 'text'               , "sum": False  },
    {"size": 10,  "group": "Bảng kê bán ra",    "name": 'Số tiền'             , 'field':"amount_am"                        , "type": 'number_int'         , "sum": True  },
    {"size": 10,  "group": "Bảng kê bán ra",    "name": 'Chênh lệch'          , 'field':"diff"                             , "type": 'number_int'         , "sum": True  },
    {"size": 15,                                "name": 'Đơn hàng'            , 'field':"order_name"                       , "type": 'text'               , "sum": False  },
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


class RpInternalTfWizardReport(models.AbstractModel):
    _name = "report.ccv_report_revenue.rp_revenue_reconciliation"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE
    
    def _get_partner(self, o):
        Partner = self.env['res.partner']
        partner_ids = Partner
        start_datetime = fields.Datetime.to_datetime(o.date_from)
        end_datetime = fields.Datetime.end_of(fields.Datetime.to_datetime(o.date_to), 'day')

        if o.report_type == 'is_all_partner':
            # Lấy partner từ account move line (công nợ)
            aml_partners = self.env['account.move.line'].search([
                ('date', '>=', start_datetime),
                ('date', '<=', end_datetime),
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', '=', 'asset_receivable'),
                ('partner_id', '!=', False),
            ]).mapped('partner_id')

            # Lấy partner từ sale order
            so_partners = self.env['stock.picking'].search([
                ('partner_id', '!=', False),
                ('stock_date_receipt', '>=', start_datetime),
                ('stock_date_receipt', '<=', end_datetime),
            ]).mapped('partner_id')

            # Hợp nhất, bỏ trùng
            partner_ids = aml_partners | so_partners

        elif o.report_type == 'team':
            # Partner từ account move của team
            aml_partners = self.env['account.move.line'].search([
                ('date', '>=', start_datetime),
                ('date', '<=', end_datetime),
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', '=', 'asset_receivable'),
                ('partner_id.team_id', '=', o.team_id.id),
            ]).mapped('partner_id')

            # Partner từ sale order của team
            so_partners = self.env['stock.picking'].search([
                ('partner_id.team_id', '=', o.team_id.id),
                ('stock_date_receipt', '>=', start_datetime),
                ('stock_date_receipt', '<=', end_datetime),
            ]).mapped('partner_id')

            partner_ids = (aml_partners | so_partners).filtered(lambda p: p)
        else:
            partner_ids = o.partner_id

        return partner_ids

    @staticmethod
    def html_to_text(html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()

    def _get_data_orderline(self, order, pks):
        lines = []
        for pk in order.picking_ids.filtered(lambda l: l in pks):
            total = 0
            for move in pk.move_ids:
                delivered_qty = move.quantity_done
                taxes_res = move.sale_line_id.tax_id.compute_all(move.sale_line_id.price_unit,quantity=delivered_qty,currency=move.sale_line_id.currency_id,product=move.product_id,partner=order.partner_id,)
                sign = 1 if move.location_dest_id.usage == 'customer' else -1
                total += taxes_res['total_included'] * sign
            if total:
                lines.append({
                    'type': 'order',
                    'picking_name': pk.name,
                    # 'picking_name': order.name,
                    'stock_date_receipt': pk.stock_date_receipt.strftime('%d/%m/%Y'),
                    'note': self.html_to_text(pk.reason_output_input_stock),
                    'amount_order': total,
                    'move_name': '',
                    'invoice_name': '',
                    'date': '',
                    'amount_am': 0,
                    'order_name': order.name,
                })
        return lines
        
    def _get_data_inv(self, invoices, order):
        lines = []
        for inv in invoices:
            sign = 1 if inv.move_type == 'out_invoice' else -1
            invoice_names = inv.name
            invoice_numbers = inv.vat_sinvoice_number or ''
            invoice_dates = inv.date.strftime('%d/%m/%Y')
            amount = sign * inv.amount_total
            if amount:
                lines.append({
                    'type': 'invoice',
                    'picking_name': '',
                    'stock_date_receipt': '',
                    'note': '',
                    'amount_order': 0,
                    'move_name': invoice_names,
                    'invoice_name': invoice_numbers,
                    'date': invoice_dates,
                    'amount_am': amount,
                    'order_name': order.name,
                })
        return lines

    def _get_diff_from_SO(self, o, partner_id):
        start_datetime = fields.Datetime.to_datetime(o.date_from)
        end_datetime = fields.Datetime.end_of(fields.Datetime.to_datetime(o.date_to), 'day')

        Picking = self.env['stock.picking']
        lines = []

        # Lọc các giao hàng đã hoàn tất trong thời gian
        pks = Picking.search([
            ('partner_id', '=', partner_id.id),
            ('stock_date_receipt', '>=', start_datetime),
            ('stock_date_receipt', '<=', end_datetime),
            ('state', '=', 'done'),
            ('sale_id', '!=', False),
        ])
        orders = pks.mapped('sale_id')
        for order in orders:
            amount_order = 0

            # Tính tổng giá trị giao hàng lệch chưa xuất hóa đơn
            for line in order.order_line:
                delivered_qty = line.qty_delivered
                invoiced_qty = line.qty_invoiced
                qty_diff = abs(delivered_qty - invoiced_qty)
                if qty_diff == 0:
                    continue
                taxes_res = line.tax_id.compute_all(line.price_unit,quantity=qty_diff,currency=line.currency_id,product=line.product_id,partner=partner_id,)
                total_line = taxes_res['total_included']
                if delivered_qty > invoiced_qty:
                    amount_order += total_line
                else:
                    amount_order -= total_line
            if not amount_order:
                continue

            # Tính tổng tiền từ các hóa đơn liên quan
            invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            amount_am = 0
            for inv in invoices:
                sign = 1 if inv.move_type == 'out_invoice' else -1
                amount_am += sign * inv.amount_total

            # Nếu chênh lệch → thêm 2 dòng: 1 dòng cho đơn, 1 dòng cho hóa đơn
            if round(amount_order, 2) != round(amount_am, 2):
                lines += self._get_data_orderline(order, pks)
                lines += self._get_data_inv(invoices, order)
        return lines

    def _get_data_export(self, obj):
        grouped = {}
        grand_totals = {
            "amount_order": 0,
            "amount_am": 0,
            "diff": 0,
        }
        partner_ids = self._get_partner(obj)
        for partner_id in partner_ids:
            datas = self._get_diff_from_SO(obj, partner_id)
            count = 0
            lines = []
            sums = {
                "amount_order": 0,
                "amount_am": 0,
                "diff": 0,
            }
            for data in datas:
                count += 1
                data.update({
                    "no": count,
                    'partner_name': partner_id.name,
                    'diff': 0,
                })
                for key, value in sums.items():
                    sums.update({key: value + data.get(key, 0)})
                lines.append(data)
            sums.update({'diff': sums.get('amount_order') - sums.get('amount_am')})
            
            if lines:
                for key, value in grand_totals.items():
                    grand_totals.update({key: value + sums.get(key, 0)})
                vals = {
                    partner_id.name: {
                        "lines": lines,
                        "sums": sums
                    },
                }
                grouped.update(vals)
                
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

    def add_header(self, sheet, formats, obj):
        row_group = 5
        row_detail = 6

        col = 0
        last_group = None
        group_start_col = 0

        for i, column in enumerate(COLUMNS):
            group = column.get("group", "")
            name = column.get("name", "")

            if not group:
                sheet.merge_range(row_group, col, row_detail, col, name, formats["header"])
            else:
                # Ghi tiêu đề con (tên cột)
                sheet.write(row_detail, col, name, formats["header"])

                is_last = (i == len(COLUMNS) - 1)
                next_group = COLUMNS[i + 1].get("group", "") if not is_last else None

                if group != last_group:
                    group_start_col = col

                if group != next_group or is_last:
                    # Merge ngang cho group
                    sheet.merge_range(row_group, group_start_col, row_group, col, group, formats["header"])

            last_group = group
            col += 1

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

        # Lặp qua từng kho trong dữ liệu
        for partner_name, partner_data in lines_data.get("grouped", {}).items():
            # Ghi tiêu đề tên kho
            sheet.merge_range(prod_row, 0, prod_row, len(COLUMNS) - 1,
                              f"KHÁCH HÀNG: {partner_name.upper()}", formats["description_bold"])
            prod_row += 1

            # Ghi các dòng dữ liệu chi tiết cho kho hiện tại
            current_warehouse_lines = partner_data.get("lines", [])
            for row in current_warehouse_lines:
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
            
            # Ghi dòng tổng cộng cho kho hiện tại (Sub-Total)
            sums = partner_data.get("sums", {})
            
            # Nhãn "TỔNG CỘNG KHÁCH HÀNG: [Tên khách]"
            sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                              f"TỔNG CỘNG KHÁCH HÀNG: {partner_name.upper()}", formats["total_text_bold"])
            
            # Ghi tổng của từng cột summable cho kho hiện tại
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
        # Thêm một dòng trống để phân tách trước tổng cộng chung
        # prod_row += 1

        grand_totals = lines_data.get("grand_totals", {})
        
        # Nhãn "TỔNG CỘNG TẤT CẢ KHÁCH HÀNG"
        sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                          "TỔNG CỘNG TẤT CẢ KHÁCH HÀNG", formats["total_text_bold"])
        
        # Ghi tổng của từng cột summable cho tất cả các kho
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
            {"role": "Người Lập", "signer": obj.voter_id.name_without_position if obj.voter_id else ""},
            {"role": "Phòng Kế toán", "signer": obj.chief_finance_id.name_without_position if obj.chief_finance_id else ""},
            {"role": "Thủ trưởng đơn vị", "signer": obj.director_id.name_without_position if obj.director_id else ""},
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
            workbook.set_properties({"title": TITLE,"author": self.env.user.name_without_position,})
            sheet.set_landscape()
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)
