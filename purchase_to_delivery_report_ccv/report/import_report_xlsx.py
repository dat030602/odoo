# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models
from odoo.modules.module import get_module_resource

import ast
import json
import logging

_logger = logging.getLogger(__name__)
TITLE = 'Chốt lô nguyên liệu'

COLUMNS = [
    {"size":  5,          "name": 'STT'                        , 'field':"no"                      , "type": 'number_c_int'       , "sum": False  },
    {"size": 15,          "name": 'Phiếu nhập kho'             , 'field':"picking_id"              , "type": 'date'               , "sum": False  },
    {"size": 10,          "name": 'Ngày'                       , 'field':"date"                    , "type": 'date'               , "sum": False  },
    {"size": 10,          "name": 'Số xe'                      , 'field':"vehicle_license_plate"   , "type": 'text'               , "sum": False  },
    {"size": 15,          "name": 'Số Cont'                    , 'field':"container_number"        , "type": 'text'               , "sum": False  },
    {"size": 15,          "name": 'Số Seal'                    , 'field':"seal_number"             , "type": 'text'               , "sum": False  },
    {"size": 25,          "name": 'Kho / Khách hàng'           , 'field':"stock_partner"           , "type": 'text'               , "sum": False  },
    {"size": 10,          "name": 'Số lượng List cont'         , 'field':"qty_list_cont"           , "type": 'number_float3'      , "sum": True  },
    {"size": 15,          "name": 'Số lượng theo chứng từ'     , 'field':"weight_receipt"          , "type": 'number_float3'      , "sum": True  },
    {"size": 10,          "name": 'Cân CCV'                    , 'field':"weight_ccv"              , "type": 'number_float3'      , "sum": True  },
    {"size": 10,          "name": 'Cân Cảng'                   , 'field':"weight_port"             , "type": 'number_float3'      , "sum": True  },
    {"size": 10,          "name": 'Số lượng bao'               , 'field':"bag_number"              , "type": 'number_int'         , "sum": True  },
    {"size": 15,          "name": 'Số lượng cân CCV trừ bì'    , 'field':"weight_ccv_net"          , "type": 'number_float3'      , "sum": True },
    {"size": 15,          "name": 'Số lượng cân Cảng trừ bì'   , 'field':"weight_port_net"         , "type": 'number_float3'      , "sum": True },
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

def init_sums():
    sums = {}
    for key in COLUMNS:
        if key.get("sum", False):
            sums[key.get("field")] = 0
    return sums

def update_sums(sums, data, lines, is_total=False):
    for key in COLUMNS:
        if key.get("sum", False):
            if not is_total and key.get("value_end", False):
                sums[key.get("field")] = lines.mapped(key.get("field"))[-1]
                continue
            sums[key.get("field")] += data.get(key.get("field"), 0)
    return sums

def safe_data(data, key, sub_key="", is_num=False):
    safe_val = 0 if is_num else ""
    value = getattr(data, key, safe_val)
    if sub_key:
        value = getattr(value, sub_key, safe_val)
    if is_num and isinstance(value, (int, float)):
        return value
    return value

class ImportDeliveryReportXlsx(models.AbstractModel):
    _name = "report.purchase_to_delivery_report_ccv.import_report_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = TITLE  

class ImportDeliveryReportCcvXlsx(models.AbstractModel):
    _name = "report.purchase_to_delivery_report_ccv.import_report_ccv_xlsx"
    _inherit = "report.purchase_to_delivery_report_ccv.import_report_xlsx"
    _description = TITLE
    
    def _get_data_export(self, obj):
        """Get organized data for export without partner grouping - similar to production report"""
        count = 0
        lines = []
        grand_totals = init_sums()
        pks = obj.delivery_picking_ids
        # pks = self.env['stock.picking']
        po = obj.purchase_id if hasattr(obj, 'purchase_id') and obj.purchase_id else self.env['purchase.order'].search([('name','=',obj.origin)])
        qty_list_cont = sum(po.order_line.mapped('product_uom_qty')) / (len(po.stock_input_ids) or 1)
        
        for pk in pks:
            count += 1
            stock_partner = pk.location_dest_id.warehouse_id.code if pk.location_dest_id.warehouse_id.code else ""
            if pk.location_dest_id.usage == 'customer':
                stock_partner = pk.partner_id.name if pk.partner_id.name else ""
            weight_ccv = pk.weight_ccv if pk.weight_ccv else 0
            weight_port = pk.weight_port if pk.weight_port else 0
            
            weight_ccv_net = weight_ccv
            weight_port_net = weight_port
            
            if pk.move_ids:
                product = pk.move_ids[0].product_id
                bag_uom = product.default_specification_id
                tare_uom = product.packaging_specification_id
                
                if bag_uom and tare_uom:
                    bag_factor = bag_uom.factor if bag_uom.uom_type == 'smaller' else (1.0 / bag_uom.factor if bag_uom.uom_type == 'bigger' else 1.0)
                    tare_factor = tare_uom.factor if tare_uom.uom_type == 'smaller' else (1.0 / tare_uom.factor if tare_uom.uom_type == 'bigger' else 1.0)
                    
                    if tare_factor != 0:
                        tare_ccv = (weight_ccv * bag_factor) / tare_factor
                        tare_port = (weight_port * bag_factor) / tare_factor
                        weight_ccv_net -= tare_ccv
                        weight_port_net -= tare_port

            vals = {
                "no": count,
                "picking_id": pk.name,
                "date": pk.stock_date_receipt.strftime('%d/%m/%Y') if pk.stock_date_receipt else "",
                "vehicle_license_plate": pk.vehicle_license_plate if pk.vehicle_license_plate else "",
                "container_number": pk.container_number if pk.container_number else "",
                "seal_number": pk.seal_number if pk.seal_number else "",
                "stock_partner": stock_partner,
                "qty_list_cont": qty_list_cont,
                "weight_receipt": pk.weight_receipt if pk.weight_receipt else 0,
                "weight_ccv": weight_ccv,
                "weight_port": weight_port,
                "bag_number": pk.bag_number if pk.bag_number else 0,
                "weight_ccv_net": weight_ccv_net,
                "weight_port_net": weight_port_net,
            }
            lines.append(vals)
            
            # Update grand totals
            grand_totals = update_sums(grand_totals, vals, pk)

        replace_zeros(grand_totals)

        return {
            "all_lines": lines,
            "grand_totals": grand_totals
        }

    def add_title(self, sheet, formats, obj):
        # Keep company name and address fixed
        sheet.merge_range("C2:O2","Công ty Cổ phần Tập đoàn Con Cò Vàng - Mã số thuế: 0305995751",formats["company_name"],)
        
        # Keep image insertion as is
        sheet.insert_image("A1",get_module_resource("ccv_bao_cao", "static/src/img", "logo.png"),{"x_offset": 0, "y_offset": 0, "x_scale": 0.22, "y_scale": 0.22},)

        # Calculate the last column letter dynamically
        last_column_letter = chr(65 + len(COLUMNS) - 1)
        
        start_row = 3
        # Adjust main title to span all columns
        text = TITLE.upper()
        sheet.merge_range(f"A{start_row + 1}:{last_column_letter}{start_row + 1}", text, formats["title_main"])
        sheet.set_row(start_row, 35)
        start_row += 1

        def add_text(text, value, row, height_row=20):
            sheet.merge_range(f"B{row + 1}:C{row + 1}", text + ": ", formats["description_bold"])
            sheet.merge_range(f"D{row + 1}:{last_column_letter}{row + 1}", value, formats["description"])
            sheet.set_row(row, height_row)
            row += 1
            return row

        po = obj.purchase_id if hasattr(obj, 'purchase_id') and obj.purchase_id else self.env['purchase.order'].search([('name','=',obj.origin)])

        start_row = add_text("Đơn mua hàng", po.name, start_row)
        start_row = add_text("Nhà cung cấp", po.partner_id.name, start_row)
        height_row = (len(po.order_line.mapped('product_id.name')) * 20) or 20
        start_row = add_text("Sản phẩm", '\n'.join(po.order_line.mapped('product_id.name')), start_row, height_row=height_row)
        
        bag_weights = [name for name in po.order_line.mapped('product_id.default_specification_id.name') if name]
        start_row = add_text("Trọng lượng bao", '\n'.join(bag_weights) if bag_weights else '', start_row, height_row=(len(bag_weights) * 20) or 20)
        
        tare_weights = [name for name in po.order_line.mapped('product_id.packaging_specification_id.name') if name]
        start_row = add_text("Định mức bao bì", '\n'.join(tare_weights) if tare_weights else '', start_row, height_row=(len(tare_weights) * 20) or 20)
        
        start_row = add_text("Số lượng", '%.3f Tấn' % (sum(po.order_line.mapped('product_uom_qty')) or 0), start_row)
        start_row = add_text("Số hợp đồng", po.partner_ref or "", start_row)
        start_row = add_text("Số tờ khai hải quan", po.custom_declaration_number or "", start_row)
        start_row = add_text("Ngày tờ khai", po.custom_declaration_date.strftime('%d/%m/%Y') if po.custom_declaration_date else "", start_row)
        
    def add_header(self, sheet, formats, obj):
        row_group = sheet.dim_rowmax + 2
        row_detail = row_group + 1

        col = 0
        last_group = None
        group_start_col = 0

        for i, column in enumerate(COLUMNS):
            group = column.get("group", "")
            name = column.get("name", "")

            if not group:
                sheet.merge_range(row_group, col, row_detail, col, name, formats["header"])
            else:
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
        row = sheet.dim_rowmax + 1
        prod_row = sheet.dim_rowmax + 1

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

        # Ghi các dòng dữ liệu chi tiết (không nhóm theo nhà cung cấp)
        all_lines = lines_data.get("all_lines", [])
        for row in all_lines:
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
                
        # --- Phần Tổng Cộng Chung (Grand Total) ---
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
            {"role": "Người Lập Phiếu", "signer": obj.voter_id.name_without_position if obj.voter_id else ""},
            {"role": "Phòng kế toán", "signer": obj.accounting_department_id.name_without_position if obj.accounting_department_id else ""},
            {"role": "Nhà máy", "signer": ", ".join([name for name in obj.factory_ids.mapped('name_without_position') if name]) if obj.factory_ids else ""},
            {"role": "Kế Toán Trưởng", "signer": obj.chief_accountant_id.name_without_position if getattr(obj, 'chief_accountant_id', False) else ""},
            {"role": "Phòng Thương mại", "signer": obj.trade_department_id.name_without_position if obj.trade_department_id else ""},
            {"role": "Thủ trưởng đơn vị", "signer": obj.unit_heads_id.name_without_position if obj.unit_heads_id else ""},
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
            
        row += 1 

        current_col_idx = 0
        for i, block in enumerate(signature_blocks):
            col_start_idx = current_col_idx
            if i == num_signature_blocks - 1:
                col_end_idx = last_column_index
            else:
                col_end_idx = col_start_idx + block_width - 1

            col_from_letter = chr(65 + col_start_idx)
            col_to_letter = chr(65 + col_end_idx)

            signature_note = "(Ký, họ tên)"
            if i == num_signature_blocks - 1:
                signature_note = "(Ký, họ tên, đóng dấu)"
            
            sheet.merge_range(f"{col_from_letter}{row}:{col_to_letter}{row}", signature_note, formats["signature_note"])

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

    def generate_xlsx_report(self, workbook, data, objects):
        for obj in objects:
            sheet = workbook.add_worksheet(TITLE)
            workbook.set_properties({"title": TITLE,"author": self.env.user.name_without_position,})
            sheet.set_footer('&"Times New Roman"&11Trang &P/&N')
            sheet.set_landscape()
            sheet.set_paper(9)
            formats = create_formats(workbook)
            self.add_title(sheet, formats, obj)
            self.add_header(sheet, formats, obj)
            self.add_body(sheet, formats, obj)
            self.add_signatures(sheet, formats, obj)