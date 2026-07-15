# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.modules.module import get_module_resource

import logging

_logger = logging.getLogger(__name__)

            # Format cho chữ
def json_format(font_size, font_name="Times New Roman", align="vcenter", right=False, left=False, bottom=False, top=False, bold=False, italic=False, num_format=False):
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
        'num_format': num_format
    }

class chi_tiet_cong_no_phai_tra(models.AbstractModel):
    _name = "report.ccv_bao_cao_cong_no.chi_tiet_cong_no_phai_tra"
    _inherit = "report.report_xlsx.abstract"
    _description = "Chi Tiet Cong No Phai Tra"
    
    def get_data_export(self, obj):
        lines_obj = obj.line2_ids
        sum_ps_credit_vnd = sum(lines_obj.mapped("ps_credit"))
        sum_ps_debit_vnd = sum(lines_obj.mapped("ps_debit"))
        sum_end_credit_vnd = 0
        sum_end_debit_vnd = 0
        sum_product_uom_quantity = 0

        lines = []
        partner_ids = lines_obj.mapped("partner_id")
        for partner_id in partner_ids:
            count = 0
            line_ids = lines_obj.filtered(lambda l: l.partner_id.id == partner_id.id)
            if line_ids:
                for data in line_ids:
                    if count == 0:
                        vals = {
                            "partner": data.partner_id.name,
                            "no": count,
                        }
                        lines.append(vals)
                        count += 1
                    uom_id = data.uom_id.name if data.uom_id else ""
                    order_id = data.order_id.name if data.order_id else ""
                    move_id = data.move_id.name if data.move_id else ""
                    date = data.date if data.date else ""
                    invoice_date = data.invoice_date if data.invoice_date else ""
                    reference = data.reference if data.reference else ""
                    product_uom_quantity = (
                        data.product_uom_quantity if data.product_uom_quantity else 0
                    )
                    price_unit = data.price_unit if data.price_unit else 0
                    note = data.note if data.note else ""
                    default_code = data.default_code if data.default_code else ""
                    account_id = data.account_id.code if data.account_id else ""
                    account_dest_id = (
                        data.account_dest_id.code if data.account_dest_id else ""
                    )
                    ps_debit_vnd = data.ps_debit
                    ps_credit_vnd = data.ps_credit
                    end_debit_vnd = data.end_debit
                    end_credit_vnd = data.end_credit
                    vals = {
                        "no": count,
                        "move_id": move_id,
                        "date": date,
                        "invoice_date": invoice_date,
                        "reference": reference,
                        "product_uom_quantity": product_uom_quantity,
                        "price_unit": price_unit,
                        "note": note,
                        "default_code": default_code,
                        "account_id": account_id,
                        "account_dest_id": account_dest_id,
                        "uom_id": uom_id,
                        "order_id": order_id,
                        "ps_debit_vnd": round(ps_debit_vnd),
                        "ps_credit_vnd": round(ps_credit_vnd),
                        "end_debit_vnd": round(end_debit_vnd),
                        "end_credit_vnd": round(end_credit_vnd),
                    }
                    count += 1
                    lines.append(vals)
                vals = {
                    "partner": data.partner_id.name,
                    "no": "sum",
                    "product_uom_quantity": round(sum(line_ids.mapped("product_uom_quantity"))),
                    "ps_debit_vnd": round(sum(line_ids.mapped("ps_debit"))),
                    "ps_credit_vnd": round(sum(line_ids.mapped("ps_credit"))),
                    "end_debit_vnd": round(line_ids[-1].end_debit),
                    "end_credit_vnd": round(line_ids[-1].end_credit),
                }
                sum_end_credit_vnd += line_ids[-1].end_credit
                sum_end_debit_vnd += line_ids[-1].end_debit
                sum_product_uom_quantity += sum(line_ids.mapped("product_uom_quantity"))
                lines.append(vals)
        return {
            "sum": {
                "sum_product_uom_quantity": round(sum_product_uom_quantity),
                "sum_ps_credit_vnd": f"{round(sum_ps_credit_vnd):,}",
                "sum_ps_debit_vnd": f"{round(sum_ps_debit_vnd):,}",
                "sum_end_credit_vnd": f"{round(sum_end_credit_vnd):,}",
                "sum_end_debit_vnd": f"{round(sum_end_debit_vnd):,}",
            },
            "lines": lines,
        }

    def generate_xlsx_report(self, workbook, data, objects):
        for obj in objects.sudo():
            date_start = obj.date_from.strftime("%d/%m/%Y")
            date_end = obj.date_to.strftime("%d/%m/%Y")
            account = (obj.account_ids + obj.account_id).mapped("code")
            partner = (obj.partner_ids + obj.partner_id).mapped("name")
            account = ",".join(account) if account else ""
            partner = ",".join(partner) if partner else ""
            data_raw = self.get_data_export(obj)
            tile_report = obj.team_id.report_name if obj.team_id else ""

            sheet = workbook.add_worksheet("CHI TIẾT CÔNG NỢ PHẢI TRẢ%s" % ((" %s" % tile_report.upper()) if tile_report else " "))

            workbook.set_properties({'title': 'Báo cáo CCV', 'author': self.env.user.name})
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

            # Format cho ngày
            font_size_date = workbook.add_format(json_format(11.5, right=True,left=True,bottom=True,top=True,num_format='dd/mm/yyyy'))
            font_size_date.set_align("center")
            font_size_date.set_text_wrap()

            # Format cho số
            font_size_8_number = workbook.add_format(json_format(10, right=True,left=True,bottom=True,top=True))
            font_size_8_number.set_align("right")
            font_size_8_number.set_num_format("#,##0")

            font_size_8_number_nt = workbook.add_format(json_format(10, right=True,left=True,bottom=True,top=True))
            font_size_8_number_nt.set_align("right")
            font_size_8_number_nt.set_num_format("#,##0.00")

            format_company_title = workbook.add_format(json_format(13))
            format_company_title.set_align("left")

            # Format cho số
            total_font_size_usd = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
            total_font_size_usd.set_align("right")
            total_font_size_usd.set_num_format("#,##0.00")

            total_font_size_3 = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
            total_font_size_3.set_align("right")
            total_font_size_3.set_num_format("#,##0.000")

            total_font_size_vnd = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
            total_font_size_vnd.set_align("right")
            total_font_size_vnd.set_num_format("#,##0")

            total_font_size_text = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
            total_font_size_text.set_text_wrap()
            total_font_size_text.set_align("left")

            # Đầu đề
            sheet.merge_range("A4:O4","CHI TIẾT CÔNG NỢ PHẢI TRẢ%s" % ((" %s" % tile_report.upper()) if tile_report else " "),format1)
            sheet.set_row(4, 35)
            sheet.set_row(5, 20)
            sheet.merge_range("A5:O5", "%s%s%s%s" % (
                    ("Tài khoản: %s;" % account),
                    ("Loại tiền: VND;"),
                    ("Khách hàng: %s;" % partner) if partner else "",
                    ("Từ ngày %s đến ngày %s" % (date_start, date_end))
                ),format21)
            sheet.merge_range("C2:O2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751", format_company_title)
            sheet.insert_image('A1', get_module_resource('ccv_bao_cao_cong_no', r'static/src/img', 'logo.png'), {'x_offset': 0, 'y_offset': 0,"x_scale": 0.22, "y_scale": 0.22})

            # Bảng
            w_row_header = 6
            header_arr = [
                {'name':"STT", "column": "A"},
                {'name':"Ngày hạch toán", "column": "B"},
                {'name':"Ngày chứng từ", "column": "C"},
                {'name':"Số chứng từ", "column": "D"},
                {'name':"Số hóa đơn", "column": "E"},
                {'name':"Diễn giải", "column": "F"},
                {'name':"Tài khoản công nợ", "column": "G"},
                {'name':"Tài khoản đối ứng", "column": "H"},
            ]
            i = 0
            for header_item in header_arr:
                sheet.merge_range(f"{header_item['column']}{w_row_header}:{header_item['column']}{w_row_header+1}", header_item['name'], format_header)
                i += 1
            header_arr = [
                {"name": "Phát sinh", "from":"I", "to":"J", "items": [{"name" : "Nợ"},{"name" : "Có"},]},
                {"name": "Số dư", "from":"K", "to":"L", "items": [{"name" : "Nợ"},{"name" : "Có"},]},
            ]
            for header_item in header_arr:
                sheet.merge_range(f"{header_item['from']}{w_row_header}:{header_item['to']}{w_row_header}", header_item['name'], format_header)
                sheet.write(w_row_header, i, header_item['items'][0]['name'], format_header)
                sheet.write(w_row_header, i + 1, header_item['items'][1]['name'], format_header)
                i += 2
            
            sheet.merge_range(f"M{w_row_header}:M{w_row_header+1}", "Số lượng", format_header)

            prod_row = 7
            sum = data_raw["sum"]
            columns = [
                {"size": 5,  "name": "no" ,                  "is_num": False},
                {"size": 15, "name": "invoice_date",         "is_num": False, "is_date": True},
                {"size": 15, "name": "date",                 "is_num": False, "is_date": True},
                {"size": 12, "name": "move_id",              "is_num": False},
                {"size": 15, "name": "reference",            "is_num": False},
                {"size": 15, "name": "note",                 "is_num": False},
                {"size": 10, "name": "account_id",           "is_num": False},
                {"size": 10, "name": "account_dest_id",      "is_num": False},
                {"size": 10, "name": "ps_debit_vnd",         "is_num": True, "currency":"vnd"},
                {"size": 10, "name": "ps_credit_vnd",        "is_num": True, "currency":"vnd"},
                {"size": 10, "name": "end_debit_vnd",        "is_num": True, "currency":"vnd"},
                {"size": 10, "name": "end_credit_vnd",       "is_num": True, "currency":"vnd"},
                {"size": 10, "name": "product_uom_quantity", "is_num": False},
            ]

            for each in data_raw["lines"]:
                prod_col = 0
                if each['no'] != 'sum' and int(each['no']) == 0:
                    prod_row += 1
                    sheet.merge_range(f"A{prod_row}:M{prod_row}", each['partner'], total_font_size_text)
                elif each['no'] == 'sum':
                    prod_row += 1
                    sheet.merge_range(f"A{prod_row}:H{prod_row}", "Tổng công nợ khách %s" % each['partner'], total_font_size_text)
                    prod_col += 8
                    prod_row -= 1
                    for column in columns:
                        if column["name"] not in ('ps_debit_vnd','ps_credit_vnd','end_debit_vnd','end_credit_vnd',):
                            continue
                        current_font = font_size_8
                        if column["is_num"]:
                            if column["currency"] == "vnd":
                                current_font = total_font_size_vnd
                            else:
                                current_font = total_font_size_usd
                        sheet.set_column(prod_col, prod_col, column["size"])
                        val = each[column["name"]]
                        if column.get("none", False) and each[column.get("none")] == "":
                            val = ""
                        if val == 0.00:
                            val = ""
                        sheet.write(prod_row, prod_col, val, current_font)
                        prod_col += 1
                    sheet.write(prod_row, prod_col, each["product_uom_quantity"] if each["product_uom_quantity"] != 0.00 else "", total_font_size_3)
                    prod_row += 1
                    prod_col += 1
                else:
                    for column in columns:
                        current_font = font_size_8
                        if column["is_num"]:
                            if column["currency"] == "vnd":
                                current_font = font_size_8_number
                            else:
                                current_font = font_size_8_number_nt
                        if column.get('is_date', False):
                            current_font = font_size_date
                        if each[column["name"]] == 'product_uom_quantity':
                            current_font = total_font_size_3
                        sheet.set_column(prod_col, prod_col, column["size"])
                        val = each[column["name"]]
                        if column.get("none", False) and each[column.get("none")] == "":
                            val = ""
                        if val == 0.00:
                            val = ""
                        sheet.write(prod_row, prod_col, val, current_font)
                        prod_col += 1
                    prod_row += 1
            # Tổng cộng

            prod_row += 1
            prod_col = 0
            sheet.merge_range(f"A{prod_row}:H{prod_row}", "Tổng cộng", total_font_size_text)

            prod_row -= 1
            prod_col += 8
            
            total_arr = [
                {"name": "sum_ps_debit_vnd", "font": "vnd"},
                {"name": "sum_ps_credit_vnd", "font": "vnd"},
                {"name": "sum_end_debit_vnd", "font": "vnd"},
                {"name": "sum_end_credit_vnd", "font": "vnd"},
            ]
            for total_item in total_arr:
                current_font = total_font_size_usd
                if total_item["font"] == "vnd":
                    current_font = total_font_size_vnd
                sheet.write(prod_row, prod_col, sum[total_item["name"]] if sum[total_item["name"]] != 0 else "", current_font)
                prod_col += 1
            sheet.write(prod_row, prod_col, sum["sum_product_uom_quantity"] if sum["sum_product_uom_quantity"] != 0 else "", total_font_size_3)
            prod_row += 1
            # Footer
            # Format cho số
            footer_font_size_title = workbook.add_format(json_format(12, bold=True))
            footer_font_size_title.set_align("center")
            footer_font_size_title.set_text_wrap()

            footer_font_size_sign = workbook.add_format(json_format(11, italic=True))
            footer_font_size_sign.set_align("center")
            footer_font_size_sign.set_text_wrap()

            prod_row = prod_row + 2
            sheet.merge_range(f"I{prod_row}:M{prod_row}","Ngày ..... tháng ..... năm .........",footer_font_size_sign)

            if obj.is_sale:
                prod_row +=1
                sheet.merge_range(f"A{prod_row}:B{prod_row}","Người Lập Biểu",footer_font_size_title)
                sheet.merge_range(f"C{prod_row}:D{prod_row}","Trưởng khu vực",footer_font_size_title)
                sheet.merge_range(f"E{prod_row}:G{prod_row}","Phòng Kinh doanh",footer_font_size_title)
                sheet.merge_range(f"H{prod_row}:J{prod_row}","Kế toán trưởng",footer_font_size_title)
                sheet.merge_range(f"K{prod_row}:M{prod_row}","Thủ trưởng đơn vị",footer_font_size_title)

                prod_row +=1
                sheet.merge_range(f"A{prod_row}:B{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"C{prod_row}:D{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"E{prod_row}:G{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"H{prod_row}:J{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"K{prod_row}:M{prod_row}","(Ký, họ tên, đóng dấu)",footer_font_size_sign)

                prod_row = prod_row + 5
                sheet.merge_range(f"A{prod_row}:B{prod_row}",obj.voter_id.name_without_position if obj.voter_id else "",footer_font_size_title)
                sheet.merge_range(f"C{prod_row}:D{prod_row}",obj.lead_team_id.name_without_position if obj.lead_team_id else "",footer_font_size_title)
                sheet.merge_range(f"E{prod_row}:G{prod_row}",obj.lead_sale_id.name_without_position if obj.lead_sale_id else "",footer_font_size_title)
                sheet.merge_range(f"H{prod_row}:J{prod_row}",obj.chief_acc_id.name_without_position if obj.chief_acc_id else "",footer_font_size_title)
                sheet.merge_range(f"K{prod_row}:M{prod_row}",obj.unit_heads_id.name_without_position if obj.unit_heads_id else "",footer_font_size_title)
            else:
                prod_row +=1
                sheet.merge_range(f"A{prod_row}:D{prod_row}","Người Lập Biểu",footer_font_size_title)
                sheet.merge_range(f"E{prod_row}:H{prod_row}","Kế Toán Trưởng",footer_font_size_title)
                sheet.merge_range(f"I{prod_row}:M{prod_row}","Thủ trưởng đơn vị",footer_font_size_title)

                prod_row +=1
                sheet.merge_range(f"A{prod_row}:D{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"E{prod_row}:H{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"I{prod_row}:M{prod_row}","(Ký, họ tên, đóng dấu)",footer_font_size_sign)

                prod_row = prod_row + 5
                sheet.merge_range(f"A{prod_row}:D{prod_row}",obj.voter_id.name_without_position if obj.voter_id else "", footer_font_size_title)
                sheet.merge_range(f"E{prod_row}:H{prod_row}",obj.chief_acc_id.name_without_position if obj.chief_acc_id else "", footer_font_size_title)
                sheet.merge_range(f"I{prod_row}:M{prod_row}",obj.unit_heads_id.name_without_position if obj.unit_heads_id else "",  footer_font_size_title)
    