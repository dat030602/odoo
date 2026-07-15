# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.modules.module import get_module_resource

import logging

_logger = logging.getLogger(__name__)

def json_format(font_size, font_name="Times New Roman", align="vcenter", right=False, left=False, bottom=False, top=False, bold=False, italic=False, *kwag):
    return {
        "font_name": font_name,
        "font_size": font_size,
        "align": align,
        "right": right,
        "left": left,
        "bottom": bottom,
        "top": top,
        "bold": bold,
        "italic": italic,
    }

class bao_cao_xuat_nhap_ton(models.AbstractModel):
    _name = "report.ccv_bao_cao_ton_kho.bien_ban_kiem_ke"
    _inherit = "report.report_xlsx.abstract"
    _description = "BIÊN BẢN KIỂM KÊ"

    def generate_xlsx_report(self, workbook, data, objects):
        report = data
        data_date = report['date']
        description = report['description']
        data_datetime = report['datetime']
        lines = report['lines']
        user_ids = report['user_ids']
        sheet = workbook.add_worksheet("BIÊN BẢN KIỂM KÊ")

        workbook.set_properties({'title': 'BIÊN BẢN KIỂM KÊ', 'author': self.env.user.display_name})
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.set_margins(0.5, 0.5, 0.3, 0.3)

        # Format cho tiêu đề
        format_title = workbook.add_format(json_format(18, bold=True))
        format_title.set_align("center")

        # Format cho tiêu đề phụ
        format_sub_title = workbook.add_format(json_format(12, bold=True, italic=True))
        format_sub_title.set_text_wrap(True)
        format_sub_title.set_align("center")

        format_company_title = workbook.add_format(json_format(12))
        format_company_title.set_align("left")
        format_company_title.set_text_wrap()

        format_right_box = workbook.add_format(json_format(10, bold=True))
        format_right_box.set_align("center")

        format_right_box2 = workbook.add_format(json_format(10, bold=True, italic=True))
        format_right_box2.set_align("center")

        ############################
        # Table

        # Format cho header
        format_header_table = workbook.add_format(json_format(11, bold=True, right=True,left=True,bottom=True,top=True))
        format_header_table.set_text_wrap(True)
        format_header_table.set_align("center")

        # Format cho chữ
        font_size_text = workbook.add_format(json_format(11.5, right=True,left=True,bottom=True,top=True))
        font_size_text.set_align("center")
        font_size_text.set_text_wrap()

        # Format cho số
        font_size_number = workbook.add_format(json_format(10, right=True,left=True,bottom=True,top=True))
        font_size_number.set_align("right")
        font_size_number.set_num_format("#,##0.000")

        total_font_size_text = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
        total_font_size_text.set_text_wrap()
        total_font_size_text.set_align("left")

        total_font_size = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
        total_font_size.set_align("right")
        total_font_size.set_num_format("#,##0.000")

        # Đầu đề
        
        sheet.merge_range("C2:F3","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751", format_company_title)
        sheet.insert_image('B1', get_module_resource('ccv_bao_cao', r'static/src/img', 'logo.png'), {'x_offset': 0, 'y_offset': 0,"x_scale": 0.22, "y_scale": 0.22})
        sheet.merge_range("G1:J1","Mẫu số: 05-VT", format_right_box)
        sheet.merge_range("G2:J2","(Ban hành theo Thông Tư số 200/2014/TT-BTC", format_right_box2)
        sheet.merge_range("G3:J3","Ngày 22/12/2014 của Bộ Tài Chính)", format_right_box2)
        sheet.merge_range("A5:J5","BIÊN BẢN KIỂM KÊ",format_title)
        sheet.set_row(4, 35)
        sheet.merge_range("A7:J7","- Thời điểm kiểm kê: %s" % data_datetime,format_company_title)
        sheet.merge_range("A8:J8","- Biên bản kiểm kê gồm:",format_company_title)

        w_row_header = 9
        for user_id in user_ids:
            sheet.merge_range("B%s:C%s" % (w_row_header,w_row_header),"- Ông bà: %s" % user_id['name'],format_company_title)
            sheet.merge_range("D%s:G%s" % (w_row_header,w_row_header),"- Chức vụ: %s" % user_id['job'],format_company_title)
            sheet.merge_range("H%s:J%s" % (w_row_header,w_row_header),"- Đại diện: %s" % user_id['representative'],format_company_title)
            w_row_header += 1

        # Bảng
        w_row_header += 1
        sheet.merge_range("A%s:J%s" % (w_row_header,w_row_header),"- Lý do kiểm kê: %s" % description,format_company_title)
        w_row_header += 1

        w_row_header += 1
        i = 0
        header_arr = [
            {'name':"STT", "column": "A"},
            {'name':"Mã hàng", "column": "B"},
            {'name':"Tên hàng", "column": "C"},
            {'name':"Đơn vị tính", "column": "D"},
        ]
        i = 0
        for header_item in header_arr:
            sheet.merge_range(f"{header_item['column']}{w_row_header}:{header_item['column']}{w_row_header+1}", header_item['name'], format_header_table)
            i += 1

        header_arr = [
            {"name": "Số lượng", "from":"E", "to":"G", "items": [{"name" : "Theo số kế toán"},{"name" : "Theo kiểm kê"},{"name" : "Chênh lệch"},]},
            {"name": "Giá trị", "from":"H", "to":"J", "items": [{"name" : "Theo số kế toán"},{"name" : "Theo kiểm kê"},{"name" : "Chênh lệch"},]},
        ]
        for header_item in header_arr:
            sheet.merge_range(f"{header_item['from']}{w_row_header}:{header_item['to']}{w_row_header}", header_item['name'], format_header_table)
            sheet.write(w_row_header, i, header_item['items'][0]['name'], format_header_table)
            sheet.write(w_row_header, i + 1, header_item['items'][1]['name'], format_header_table)
            sheet.write(w_row_header, i + 2, header_item['items'][2]['name'], format_header_table)
            i += 3

        prod_row = w_row_header + 1
        sum = report["sum"]
        columns = [
            {"size": 5,     "name": "no" ,                            "is_num": False},
            {"size": 20,    "name": "default_code",                   "is_num": False},
            {"size": 30,    "name": "product_id",                     "is_num": False},
            {"size": 15,   "name": "uom_id",                          "is_num": False},
            {"size": 10,     "name": "stock_quantity",                "is_num": True},
            {"size": 10,     "name": "stock_inventory_quantity",      "is_num": True},
            {"size": 10,     "name": "stock_diff_quantity",           "is_num": True},
            {"size": 10,     "name": "value_quantity",                "is_num": True},
            {"size": 10,     "name": "value_inventory_quantity",      "is_num": True},
            {"size": 10,     "name": "value_diff_quantity",           "is_num": True},
        ]
        for each in lines:
            prod_col = 0
            for column in columns:
                current_font = font_size_text
                if column["is_num"]:
                    current_font = font_size_number
                sheet.set_column(prod_col, prod_col, column["size"])
                val = each[column["name"]]
                sheet.write(prod_row, prod_col, val, current_font)
                prod_col += 1
            prod_row += 1
        # Tổng cộng

        prod_row += 1
        prod_col = 0
        sheet.merge_range(f"A{prod_row}:D{prod_row}", "Tổng cộng", total_font_size_text)

        prod_row -= 1
        prod_col += 4
        total_arr = [
            {"name": "sum_stock_quantity"},
            {"name": "sum_stock_inventory_quantity"},
            {"name": "sum_stock_diff_quantity"},
            {"name": "sum_value_quantity"},
            {"name": "sum_value_inventory_quantity"},
            {"name": "sum_value_diff_quantity"},
        ]
        for total_item in total_arr:
            sheet.write(prod_row, prod_col, sum[total_item["name"]], total_font_size)
            prod_col += 1

        footer_font_size_title = workbook.add_format(json_format(11, bold=True))
        footer_font_size_title.set_align("center")
        footer_font_size_title.set_text_wrap()

        footer_font_size_sign = workbook.add_format(json_format(11, italic=True))
        footer_font_size_sign.set_align("center")
        footer_font_size_sign.set_text_wrap()

        footer_font_size_sign1 = workbook.add_format(json_format(11))
        footer_font_size_sign1.set_align("center")
        footer_font_size_sign1.set_text_wrap()

        prod_row = prod_row + 2
        sheet.merge_range(f"G{prod_row}:J{prod_row}",data_date,footer_font_size_sign)

        prod_row +=1
        sheet.merge_range(f"A{prod_row}:B{prod_row}","Thủ trưởng đơn vị",footer_font_size_title)
        sheet.write(prod_row - 1, 2, 'Kế Toán Trưởng', footer_font_size_title)
        sheet.merge_range(f"D{prod_row}:F{prod_row}","Thủ kho/Tổ trưởng nhà máy",footer_font_size_title)
        sheet.merge_range(f"G{prod_row}:H{prod_row}","Ban kiểm kê",footer_font_size_title)
        sheet.merge_range(f"I{prod_row}:J{prod_row}","Người lập phiếu",footer_font_size_title)

        prod_row +=1
        sheet.merge_range(f"A{prod_row}:B{prod_row}","Ý kiến giải quyết",footer_font_size_sign1)
        sheet.write(prod_row - 1, 2, '(Ký, họ tên)', footer_font_size_sign)
        sheet.merge_range(f"D{prod_row}:F{prod_row}","(Ký, họ tên)",footer_font_size_sign)
        sheet.merge_range(f"G{prod_row}:H{prod_row}","(Ký, họ tên)",footer_font_size_sign)
        sheet.merge_range(f"I{prod_row}:J{prod_row}","(Ký, họ tên)",footer_font_size_sign)

        prod_row +=1
        sheet.merge_range(f"A{prod_row}:B{prod_row}","số chênh lệch",footer_font_size_sign1)
        prod_row +=1
        sheet.merge_range(f"A{prod_row}:B{prod_row}","(Ký, họ tên)",footer_font_size_sign)
        
