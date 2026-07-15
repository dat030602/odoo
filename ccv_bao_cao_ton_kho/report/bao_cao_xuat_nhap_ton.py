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
    _name = "report.ccv_bao_cao_ton_kho.bao_cao_xuat_nhap_ton"
    _inherit = "report.report_xlsx.abstract"
    _description = "Báo cáo xuất nhập tồn"

    def generate_xlsx_report(self, workbook, data, objects):
        report = data
        date_from = report['date_from']
        date_to = report['date_to']
        inventories = report['inventories']
        data_raw = report['data']
        sheet = workbook.add_worksheet("BÁO CÁO XUẤT NHẬP TỒN TỪ NGÀY %s ĐẾN NGÀY %s" % (date_from,date_to))

        workbook.set_properties({'title': 'Báo cáo CCV', 'author': self.env.user.display_name})
        sheet.set_landscape()

        # Format cho tiêu đề
        format1 = workbook.add_format(json_format(16, bold=True))
        format1.set_align("center")

        # Format cho tiêu đề phụ
        format21 = workbook.add_format(json_format(12, bold=True, italic=True))
        format21.set_text_wrap(True)
        format21.set_align("center")

        # Format cho header
        format_header = workbook.add_format(json_format(11, bold=True, right=True,left=True,bottom=True,top=True))
        format_header.set_text_wrap(True)
        format_header.set_align("center")

        # Format cho chữ
        font_size_8 = workbook.add_format(json_format(11.5, right=True,left=True,bottom=True,top=True))
        font_size_8.set_align("center")
        font_size_8.set_text_wrap()
        # Format cho số
        font_size_8_number = workbook.add_format(json_format(10, right=True,left=True,bottom=True,top=True))
        font_size_8_number.set_align("right")
        font_size_8_number.set_num_format("#,##0.000")

        format_company_title = workbook.add_format(json_format(13))
        format_company_title.set_align("left")

        total_font_size_text = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
        total_font_size_text.set_text_wrap()
        total_font_size_text.set_align("left")

        total_font_size_text_location = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
        total_font_size_text_location.set_text_wrap()
        total_font_size_text_location.set_align("left")
        total_font_size_text_location.set_bg_color('#FFFF00')

        total_font_size_text_product = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
        total_font_size_text_product.set_text_wrap()
        total_font_size_text_product.set_align("left")
        total_font_size_text_product.set_bg_color('#C4D79B')

        total_font_size = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
        total_font_size.set_align("right")
        total_font_size.set_num_format("#,##0.000")

        # Đầu đề
        sheet.merge_range("A4:J4","BÁO CÁO XUẤT NHẬP TỒN",format1)
        sheet.set_row(4, 35)
        sheet.set_row(5, 20)
        sheet.merge_range("A5:J5", "%s;%s" % (
                ("Kho: %s" % inventories),
                ("Từ ngày %s đến ngày %s" % (date_from, date_to))
            ),format21)
        sheet.merge_range("C2:J2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751", format_company_title)
        sheet.insert_image('A1', get_module_resource('ccv_bao_cao', r'static/src/img', 'logo.png'), {'x_offset': 0, 'y_offset': 0,"x_scale": 0.22, "y_scale": 0.22})

        # Bảng
        w_row_header = 6
        i = 0
        header_arr = [
            {'name':"STT", "column": "A"},
            {'name':"Ngày", "column": "B"},
            {'name':"Phiếu xuất", "column": "C"},
            {'name':"Mã tham chiếu", "column": "D"},
            {'name':"Vị trí nguồn", "column": "E"},
            {'name':"Vị trí đích", "column": "F"},
            {'name':"Nguồn gốc", "column": "G"},
            {'name':"Số lượng nhập", "column": "H"},
            {'name':"Số lượng xuất", "column": "I"},
            {'name':"Tồn kho", "column": "J"},
        ]
        i = 0
        for header_item in header_arr:
            sheet.merge_range(f"{header_item['column']}{w_row_header}:{header_item['column']}{w_row_header+1}", header_item['name'], format_header)
            i += 1
        prod_row = 7
        sum = data_raw["sum"]
        columns = [
            {"size": 5,  "name": "no" ,                  "is_num": False},
            {"size": 20, "name": "date",                 "is_num": False},
            {"size": 20, "name": "picking_id",           "is_num": False},
            {"size": 20, "name": "ref",                  "is_num": False},
            {"size": 25, "name": "location_id",          "is_num": False},
            {"size": 25, "name": "location_dest_id",     "is_num": False},
            {"size": 30, "name": "origin",               "is_num": False},
            {"size": 15, "name": "to_qty_done",          "is_num": True},
            {"size": 15, "name": "from_qty_done",        "is_num": True},
            {"size": 15, "name": "stock_quant_qty",      "is_num": True},
        ]
        for each in data_raw["lines"]:
            prod_col = 0
            if each['no'] != 'sum' and (int(each['no']) == 0 or int(each['no']) == -1):
                prod_row += 1
                if int(each['no']) == -1:
                    current_font = total_font_size_text_location
                else:
                    current_font = total_font_size_text_product
                sheet.merge_range(f"A{prod_row}:J{prod_row}", each['location_origin_id'], current_font)
            elif each['no'] == 'sum':
                prod_row += 1
                sheet.merge_range(f"A{prod_row}:G{prod_row}", "Tổng cộng %s" % each['location_origin_id'], total_font_size_text)
                prod_col += 7
                prod_row -= 1
                for column in columns:
                    if column["name"] in ('to_qty_done','from_qty_done','stock_quant_qty'):
                        current_font = total_font_size
                        sheet.set_column(prod_col, prod_col, column["size"])
                        val = each[column["name"]]
                        sheet.write(prod_row, prod_col, val, current_font)
                        prod_col += 1
                prod_row += 1
            else:
                for column in columns:
                    current_font = font_size_8
                    if column["is_num"]:
                        current_font = font_size_8_number
                    sheet.set_column(prod_col, prod_col, column["size"])
                    val = each[column["name"]]
                    if column.get("none", False) and each[column.get("none")] == "":
                        val = ""
                    sheet.write(prod_row, prod_col, val, current_font)
                    prod_col += 1
                prod_row += 1
        # Tổng cộng

        prod_row += 1
        prod_col = 0
        sheet.merge_range(f"A{prod_row}:G{prod_row}", "Tổng cộng", total_font_size_text)

        prod_row -= 1
        prod_col += 7
        total_arr = [
            {"name": "sum_to_qty_done"},
            {"name": "sum_from_qty_done"},
            {"name": "sum_quant"},
        ]
        for total_item in total_arr:
            sheet.write(prod_row, prod_col, sum[total_item["name"]], total_font_size)
            prod_col += 1
