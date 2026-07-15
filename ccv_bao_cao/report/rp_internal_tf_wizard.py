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
TITLE = 'Sổ chi tiết nhập hàng'


COLUMNS = [
    {"size":  5,  "name": 'STT'                 , 'field':"no"                               , "type": 'number_c_int'       , "sum": False  },
    {"size": 12,  "name": 'Ngày chứng từ'       , 'field':"date"                             , "type": 'date'               , "sum": False  },
    {"size": 15,  "name": 'Số chứng từ'         , 'field':"name"                             , "type": 'text'               , "sum": False  },
    {"size": 25,  "name": 'Tên nhà cung cấp'    , 'field':"partner_name"                     , "type": 'text'               , "sum": False  },
    {"size": 15,  "name": 'Mã hàng'             , 'field':"product_code"                     , "type": 'text'               , "sum": False  },
    {"size": 25,  "name": 'Tên hàng'            , 'field':"product_name"                     , "type": 'text'               , "sum": False  },
    {"size": 10,  "name": 'ĐVT'                 , 'field':"uom_name"                         , "type": 'text'               , "sum": False  },
    {"size": 10,  "name": 'Số lượng nhập'       , 'field':"quantity"                         , "type": 'number_float3'      , "sum": True   },
    {"size": 10,  "name": 'Tỷ giá'              , 'field':"exchange_rate"                    , "type": 'number_int'         , "sum": False  },
    {"size": 10,  "name": 'Đơn giá NT'          , 'field':"price_unit_w_currency"            , "type": 'number_float2'      , "sum": False  },
    {"size": 10,  "name": 'Đơn giá'             , 'field':"price_unit"                       , "type": 'number_int'         , "sum": False  },
    {"size": 10,  "name": 'Giá trị mua NT'      , 'field':"amount_total_w_currency"          , "type": 'number_float2'      , "sum": True   },
    {"size": 10,  "name": 'Giá trị mua'         , 'field':"amount_total"                     , "type": 'number_int'         , "sum": True   },
    {"size": 10,  "name": 'Số lượng trả lại'    , 'field':"return_quantity"                  , "type": 'number_float3'      , "sum": True   },
    {"size": 10,  "name": 'Giá trị trả lại NT'  , 'field':"amount_total_return_w_currency"   , "type": 'number_float2'      , "sum": True   },
    {"size": 10,  "name": 'Giá trị trả lại'     , 'field':"amount_total_return"              , "type": 'number_int'         , "sum": True   },
    {"size": 10,  "name": 'Mã kho'              , 'field':"warehouse_code"                   , "type": 'text'               , "sum": False  },
    {"size": 10,  "name": 'TK Kho'              , 'field':"account"                          , "type": 'text'               , "sum": False  },
    {"size": 10,  "name": 'TK Đối ứng'          , 'field':"account_ctp"                      , "type": 'text'               , "sum": False  },
    {"size": 10,  "name": 'Đơn mua hàng'        , 'field':"order"                            , "type": 'text'               , "sum": False  },
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


class RpInternalTfWizardReport(models.AbstractModel):
    _name = "report.ccv_bao_cao.rp_internal_tf_wizard_report"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE

    @staticmethod
    def html_to_text(html_content):
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator="\n").strip()

    def _get_order_info(self, warehouse_id, sm):
        # sm = self.env['stock.move']
        if not sm or not sm.picking_id:
            return

        is_return = warehouse_id.id == sm.location_id.warehouse_id.id

        reason_output_input_stock = sm.picking_id.reason_output_input_stock
        origin = sm.picking_id.origin

        customs_declaration_number = None

        purchase_order = None

        if not is_return:
            quantity = sm.quantity_done
            return_quantity = 0
        else:
            quantity = 0
            return_quantity = sm.quantity_done

        if origin and origin.startswith('PO'):
            purchase_order = self.env['purchase.order'].search([('name', '=', origin)], limit=1)
        
        if not purchase_order:
            if reason_output_input_stock:
                # Updated Regex:
                # r'STK\s*[:]?\s*(\d+)'
                # - STK: Matches the literal "STK"
                # - \s*: Matches zero or more whitespace characters (for extra spaces)
                # - [:]?: Matches an optional colon (:)
                # - \s*: Matches zero or more whitespace characters again
                # - (\d+): Captures one or more digits (the customs declaration number)
                reason_output_input_stock = self.html_to_text(reason_output_input_stock)
                stk_match = re.search(r'STK\s*[:]?\s*(\d+)', reason_output_input_stock)
                if stk_match:
                    customs_declaration_number = stk_match.group(1)
                    am = self.env['account.move'].search([('ref','ilike',customs_declaration_number)])
                    invl = am.invoice_line_ids.filtered(lambda l:l.product_id == sm.product_id)
                    if invl and invl.purchase_line_id:
                        purchase_order = invl.purchase_line_id.order_id
                    else:
                        pk = self.env['stock.picking'].search([('purchase_id','!=',False),('reason_output_input_stock','ilike',customs_declaration_number)])
                        if pk:
                            pk = pk[0]
                            purchase_order = pk.purchase_id


        # --- 3. Return the info ---
        # Remember to replace these static values with actual data from the 'purchase_order' object
        val = {
            "exchange_rate": 0,
            "price_unit": 0,
            "amount_total": 0,
            "amount_total_return": 0,
            "price_unit_w_currency": 0,
            "amount_total_w_currency": 0,
            "amount_total_return_w_currency": 0,
            "order": "",
            "quantity": quantity,
            "return_quantity": return_quantity,
        }
        if purchase_order:
            purchase_order = purchase_order[0]
            exchange_rate = purchase_order.inverse_manural_currency_exchange_rate if purchase_order.apply_manual_currency_exchange else 0
            order_line = purchase_order.order_line.filtered(lambda l:l.product_id == sm.product_id)
            if order_line:
                order_line = order_line[0]
                price_unit = order_line.price_unit

                price_unit_w = price_unit * exchange_rate if purchase_order.apply_manual_currency_exchange else price_unit
                price_unit_w_currency = price_unit if purchase_order.apply_manual_currency_exchange else 0

                amount_total = 0
                amount_total_w_currency = 0
                amount_total_return = 0
                amount_total_return_w_currency = 0
                if not is_return:
                    amount_total = price_unit_w * quantity if purchase_order.apply_manual_currency_exchange else price_unit_w * quantity
                    amount_total_w_currency = price_unit_w_currency * quantity if purchase_order.apply_manual_currency_exchange else 0
                else:
                    amount_total_return = price_unit_w * return_quantity if purchase_order.apply_manual_currency_exchange else price_unit_w * return_quantity
                    amount_total_return_w_currency = price_unit_w_currency * return_quantity if purchase_order.apply_manual_currency_exchange else 0

                val.update({
                    "exchange_rate": exchange_rate,
                    "price_unit": price_unit_w,
                    "amount_total": amount_total,
                    "amount_total_return": amount_total_return,
                    "price_unit_w_currency": price_unit_w_currency,
                    "amount_total_w_currency": amount_total_w_currency,
                    "amount_total_return_w_currency": amount_total_return_w_currency,
                    "order": purchase_order.name,
                    "partner_name": purchase_order.partner_id.name,
                })
        return val

    def _get_data_export(self, obj):
        # obj = self.env['rp.internal.tf.wizard']
        start_datetime = fields.Datetime.to_datetime(obj.date_from)
        end_datetime = fields.Datetime.end_of(fields.Datetime.to_datetime(obj.date_to), 'day')
        grouped_warehouses = {}
        grand_totals = {
            "quantity": 0,
            "amount_total_w_currency": 0,
            "amount_total": 0,
            "amount_total_return_w_currency": 0,
            "amount_total_return": 0,
        }
        warehouse_ids = obj.warehouse_ids if obj.warehouse_ids else self.env['stock.warehouse'].search([])
        for warehouse_id in warehouse_ids:
            sm_env = self.env['stock.move']
            sms = sm_env.search([
                ('picking_id', '!=', False),
                ('picking_id.stock_date_receipt', '>=', start_datetime),
                ('picking_id.stock_date_receipt', '<=', end_datetime),
                '|',
                ('location_id.warehouse_id', '=', warehouse_id.id),
                ('location_dest_id.warehouse_id', '=', warehouse_id.id),
                ('state', '=', 'done'),
                '|',
                ('picking_id.purchase_id', '!=', False),
                ('picking_id.purchase_order_id', '!=', False),
            ]).sorted('date')


            count = 0
            lines = []
            warehouse_sums = {
                'quantity': 0,
                'amount_total_w_currency': 0,
                'amount_total': 0,
                'amount_total_return_w_currency': 0,
                'amount_total_return': 0,
            }
            for sm in sms:
                count += 1
                val = {
                    "no": count,
                    "date": sm.date,
                    "name": sm.reference,
                    "partner_name": sm.partner_id.name if sm.partner_id else "",
                    "product_code": sm.product_id.default_code if sm.product_id.default_code else "",
                    "product_name": sm.product_id.name,
                    "uom_name": sm.product_uom.name,
                    "warehouse_code": warehouse_id.code,
                    "account": sm.account_id.code if sm.account_id else "",
                    "account_ctp": ",".join(sm.account_dest_ids.mapped('code')) if sm.account_dest_ids else "",
                }
                val.update(self._get_order_info(warehouse_id, sm))
                if val.get('order', '') != '':
                    for key, value in warehouse_sums.items():
                        warehouse_sums.update({key: value + val.get(key, 0)})
                    lines.append(val)

            if lines:
                for key, value in grand_totals.items():
                    grand_totals.update({key: value + warehouse_sums.get(key, 0)})
                vals = {
                    warehouse_id.name: {
                        "lines": lines,
                        "warehouse_sums": warehouse_sums
                    },
                }
                grouped_warehouses.update(vals)
        return {
            "grouped_warehouses": grouped_warehouses,
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

        # Prepare warehouse information
        warehouse = obj.warehouse_ids.mapped("name")
        warehouse = ",".join(warehouse) if warehouse else "Tất cả"
        
        # Adjust subtitle to span all columns
        title_text = "Kho: %s; Từ ngày %s đến ngày %s" % (warehouse,obj.date_from.strftime("%d/%m/%Y"),obj.date_to.strftime("%d/%m/%Y"),)
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

        # Lặp qua từng kho trong dữ liệu
        for warehouse_name, warehouse_data in lines_data.get("grouped_warehouses", {}).items():
            # Ghi tiêu đề tên kho
            sheet.merge_range(prod_row, 0, prod_row, len(COLUMNS) - 1,
                              f"KHO: {warehouse_name.upper()}", formats["description_bold"])
            prod_row += 1

            # Ghi các dòng dữ liệu chi tiết cho kho hiện tại
            current_warehouse_lines = warehouse_data.get("lines", [])
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
            warehouse_sums = warehouse_data.get("warehouse_sums", {})
            
            # Nhãn "TỔNG CỘNG KHO: [Tên Kho]"
            sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                              f"TỔNG CỘNG KHO: {warehouse_name.upper()}", formats["total_text_bold"])
            
            # Ghi tổng của từng cột summable cho kho hiện tại
            for col_idx, column_def in enumerate(COLUMNS):
                if column_def['sum']:
                    field_name = column_def.get('field')
                    sum_value = warehouse_sums.get(field_name, 0)
                    
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
        
        # Nhãn "TỔNG CỘNG TẤT CẢ KHO"
        sheet.merge_range(prod_row, 0, prod_row, merge_label_col_end_idx, 
                          "TỔNG CỘNG TẤT CẢ KHO", formats["total_text_bold"])
        
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
            {"role": "Phòng Thương mại", "signer": obj.chief_trade_id.name_without_position if obj.chief_trade_id else ""},
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
