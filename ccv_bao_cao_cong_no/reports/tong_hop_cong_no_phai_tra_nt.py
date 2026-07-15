# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.modules.module import get_module_resource

import logging

_logger = logging.getLogger(__name__)

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

class tong_hop_cong_no_phai_tra_nt(models.AbstractModel):
    _name = "report.ccv_bao_cao_cong_no.tong_hop_cong_no_phai_tra_nt"
    _inherit = "report.report_xlsx.abstract"
    _description = "Tong Hop Cong No Phai Tra"

    def get_data_export(self, obj):
        lines_obj = obj.line2_th_nt_ids
        sum_start_credit_usd = sum(lines_obj.mapped("start_credit_nt"))
        sum_start_debit_usd = sum(lines_obj.mapped("start_debit_nt"))
        sum_ps_credit_usd = sum(lines_obj.mapped("ps_credit_nt"))
        sum_ps_debit_usd = sum(lines_obj.mapped("ps_debit_nt"))
        sum_end_credit_usd = sum(lines_obj.mapped("end_credit_nt"))
        sum_end_debit_usd = sum(lines_obj.mapped("end_debit_nt"))

        sum_start_credit_vnd = sum(lines_obj.mapped("start_credit"))
        sum_start_debit_vnd = sum(lines_obj.mapped("start_debit"))
        sum_ps_credit_vnd = sum(lines_obj.mapped("ps_credit"))
        sum_ps_debit_vnd = sum(lines_obj.mapped("ps_debit"))
        sum_end_credit_vnd = sum(lines_obj.mapped("end_credit"))
        sum_end_debit_vnd = sum(lines_obj.mapped("end_debit"))

        lines = []
        count = 1
        for data in lines_obj:
            customer_name = data.partner_name if data.partner_name else ""
            customer_code = data.partner_code if data.partner_code else ""
            address = data.address if data.address else ""
            vat = data.vat if data.vat else ""
            account_id = data.account_id.code if data.account_id else ""
            start_debit_usd = data.start_debit_nt
            start_debit_vnd = data.start_debit
            start_credit_usd = data.start_credit_nt
            start_credit_vnd = data.start_credit
            ps_debit_usd = data.ps_debit_nt
            ps_debit_vnd = data.ps_debit
            ps_credit_usd = data.ps_credit_nt
            ps_credit_vnd = data.ps_credit
            end_debit_usd = data.end_debit_nt
            end_debit_vnd = data.end_debit
            end_credit_usd = data.end_credit_nt
            end_credit_vnd = data.end_credit

            if (
                start_credit_usd == 0
                and start_debit_usd == 0
                and ps_credit_usd == 0
                and ps_debit_usd == 0
            ):
                continue
            vals = {
                "no": count,
                "customer_code": customer_code,
                "customer_name": customer_name,
                "address": address,
                "vat": vat,
                "account_id": account_id,
                "start_debit_usd": round(start_debit_usd, 2),
                "start_debit_vnd": round(start_debit_vnd),
                "start_credit_usd": round(start_credit_usd, 2),
                "start_credit_vnd": round(start_credit_vnd),
                "ps_debit_usd": round(ps_debit_usd, 2),
                "ps_debit_vnd": round(ps_debit_vnd),
                "ps_credit_usd": round(ps_credit_usd, 2),
                "ps_credit_vnd": round(ps_credit_vnd),
                "end_debit_usd": round(end_debit_usd, 2),
                "end_debit_vnd": round(end_debit_vnd),
                "end_credit_usd": round(end_credit_usd, 2),
                "end_credit_vnd": round(end_credit_vnd),
            }
            count += 1
            lines.append(vals)
        return {
            "sum": {
                "sum_start_credit_vnd": round(sum_start_credit_vnd),
                "sum_start_debit_vnd": round(sum_start_debit_vnd),
                "sum_ps_credit_vnd": round(sum_ps_credit_vnd),
                "sum_ps_debit_vnd": round(sum_ps_debit_vnd),
                "sum_end_credit_vnd": round(sum_end_credit_vnd),
                "sum_end_debit_vnd": round(sum_end_debit_vnd),
                "sum_start_credit_usd": round(sum_start_credit_usd, 2),
                "sum_start_debit_usd": round(sum_start_debit_usd, 2),
                "sum_ps_credit_usd": round(sum_ps_credit_usd, 2),
                "sum_ps_debit_usd": round(sum_ps_debit_usd, 2),
                "sum_end_credit_usd": round(sum_end_credit_usd, 2),
                "sum_end_debit_usd": round(sum_end_debit_usd, 2),
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
            
            sheet = workbook.add_worksheet("TỔNG HỢP CÔNG NỢ PHẢI TRẢ%s" % ((" %s" % tile_report.upper()) if tile_report else " "))

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

            # Đầu đề
            sheet.merge_range("A4:R4","TỔNG HỢP CÔNG NỢ PHẢI TRẢ%s" % ((" %s" % tile_report.upper()) if tile_report else " "),format1)
            sheet.set_row(4, 35)
            sheet.set_row(5, 20)
            sheet.merge_range("A5:R5","Tài khoản: %s; Loại tiền: USD; Từ ngày %s đến ngày %s" % (account,date_start,date_end),format21)
            sheet.merge_range("C2:R2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751", format_company_title)
            sheet.insert_image('A1', get_module_resource('ccv_bao_cao_cong_no', r'static/src/img', 'logo.png'), {'x_offset': 0, 'y_offset': 0,"x_scale": 0.22, "y_scale": 0.22})

            # Bảng
            w_row_header = 6
            header_arr = [
                {'name':"STT", "column": "A"},
                {'name':"Mã nhà cung cấp", "column": "B"},
                {'name':"Tên nhà cung cấp", "column": "C"},
                {'name':"Địa chỉ", "column": "D"},
                {'name':"Mã số thuế", "column": "E"},
                {'name':"Tài khoản công nợ", "column": "F"},
            ]
            i = 0
            for header_item in header_arr:
                sheet.merge_range(f"{header_item['column']}{w_row_header}:{header_item['column']}{w_row_header+1}", header_item['name'], format_header)
                i += 1
            header_arr = [
                {"name": "Dư Nợ đầu kỳ", "from":"G", "to":"H", "items": [{"name" : "Số tiền"},{"name" : "Quy đổi"},]},
                {"name": "Dư Có đầu kỳ", "from":"I", "to":"J", "items": [{"name" : "Số tiền"},{"name" : "Quy đổi"},]},
                {"name": "Phát sinh Nợ", "from":"K", "to":"L", "items": [{"name" : "Số tiền"},{"name" : "Quy đổi"},]},
                {"name": "Phát sinh Có", "from":"M", "to":"N", "items": [{"name" : "Số tiền"},{"name" : "Quy đổi"},]},
                {"name": "Dư Nợ cuối kỳ", "from":"O", "to":"P", "items": [{"name" : "Số tiền"},{"name" : "Quy đổi"},]},
                {"name": "Dư Có cuối kỳ", "from":"Q", "to":"R", "items": [{"name" : "Số tiền"},{"name" : "Quy đổi"},]},
            ]
            for header_item in header_arr:
                sheet.merge_range(f"{header_item['from']}{w_row_header}:{header_item['to']}{w_row_header}", header_item['name'], format_header)
                sheet.write(w_row_header, i, header_item['items'][0]['name'], format_header)
                sheet.write(w_row_header, i + 1, header_item['items'][1]['name'], format_header)
                i += 2

            prod_row = 7
            sum = data_raw["sum"]

            columns = [
                {"size": 5, "name": "no", "is_num": False},
                {"size": 12, "name": "customer_code", "is_num": False},
                {"size": 25, "name": "customer_name", "is_num": False},
                {"size": 25, "name": "address", "is_num": False},
                {"size": 15, "name": "vat", "is_num": False},
                {"size": 10, "name": "account_id", "is_num": False},
                {"size": 10, "name": "start_debit_usd", "is_num": True, "currency": "usd"},
                {"size": 10, "name": "start_debit_vnd", "is_num": True, "currency": "vnd"},
                {"size": 10, "name": "start_credit_usd", "is_num": True, "currency": "usd"},
                {"size": 10, "name": "start_credit_vnd", "is_num": True, "currency": "vnd"},
                {"size": 10, "name": "ps_debit_usd", "is_num": True, "currency": "usd"},
                {"size": 10, "name": "ps_debit_vnd", "is_num": True, "currency": "vnd"},
                {"size": 10, "name": "ps_credit_usd", "is_num": True, "currency": "usd"},
                {"size": 10, "name": "ps_credit_vnd", "is_num": True, "currency": "vnd"},
                {"size": 10, "name": "end_debit_usd", "is_num": True, "currency": "usd"},
                {"size": 10, "name": "end_debit_vnd", "is_num": True, "currency": "vnd"},
                {"size": 10, "name": "end_credit_usd", "is_num": True, "currency": "usd"},
                {"size": 10, "name": "end_credit_vnd", "is_num": True, "currency": "vnd"},
            ]

            for each in data_raw["lines"]:
                prod_col = 0
                for column in columns:
                    current_font = font_size_8
                    if column["is_num"]:
                        if column["currency"] == "vnd":
                            current_font = font_size_8_number
                        else:
                            current_font = font_size_8_number_nt
                    sheet.set_column(prod_col, prod_col, column["size"])
                    val = each[column["name"]]
                    if val == 0.00:
                        val = ""
                    sheet.write(prod_row, prod_col, val, current_font)
                    prod_col += 1
                prod_row +=1
            # Tổng cộng
            # Format cho số
            total_font_size_usd = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
            total_font_size_usd.set_align("right")
            total_font_size_usd.set_num_format("#,##0.00")

            total_font_size_vnd = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
            total_font_size_vnd.set_align("right")
            total_font_size_vnd.set_num_format("#,##0")

            total_font_size_text = workbook.add_format(json_format(10, right=True, left=True, bottom=True, top=True, bold=True))
            total_font_size_text.set_text_wrap()
            total_font_size_text.set_align("left")

            prod_row += 1
            prod_col = 0
            sheet.merge_range(f"A{prod_row}:F{prod_row}", "Tổng cộng", total_font_size_text)

            prod_row -= 1
            prod_col += 6
            total_arr = [
                {"name": "sum_start_debit_usd", "font": "usd"},
                {"name": "sum_start_debit_vnd", "font": "vnd"},
                {"name": "sum_start_credit_usd", "font": "us"},
                {"name": "sum_start_credit_vnd", "font": "vn"},
                {"name": "sum_ps_debit_usd", "font": "usd"},
                {"name": "sum_ps_debit_vnd", "font": "vnd"},
                {"name": "sum_ps_credit_usd", "font": "usd"},
                {"name": "sum_ps_credit_vnd", "font": "vnd"},
                {"name": "sum_end_debit_usd", "font": "usd"},
                {"name": "sum_end_debit_vnd", "font": "vnd"},
                {"name": "sum_end_credit_usd", "font": "usd"},
                {"name": "sum_end_credit_vnd", "font": "vnd"},
            ]
            for total_item in total_arr:
                current_font = total_font_size_usd
                if total_item["font"] == "vnd":
                    current_font = total_font_size_vnd
                val = sum[total_item["name"]]
                if val == 0.00:
                    val = ""
                sheet.write(prod_row, prod_col, val, current_font)
                prod_col += 1
            prod_row +=1
            # Footer
            # Format cho số
            footer_font_size_title = workbook.add_format(json_format(12, bold=True))
            footer_font_size_title.set_align("center")
            footer_font_size_title.set_text_wrap()

            footer_font_size_sign = workbook.add_format(json_format(11, italic=True))
            footer_font_size_sign.set_align("center")
            footer_font_size_sign.set_text_wrap()

            prod_row = prod_row + 2
            sheet.merge_range(f"O{prod_row}:R{prod_row}","Ngày ..... tháng ..... năm .........",footer_font_size_sign)

            if obj.is_sale:
                prod_row +=1
                sheet.merge_range(f"A{prod_row}:C{prod_row}","Người Lập Biểu",footer_font_size_title)
                sheet.merge_range(f"D{prod_row}:F{prod_row}","Trưởng khu vực",footer_font_size_title)
                sheet.merge_range(f"G{prod_row}:J{prod_row}","Phòng Kinh doanh",footer_font_size_title)
                sheet.merge_range(f"K{prod_row}:N{prod_row}","Kế toán trưởng",footer_font_size_title)
                sheet.merge_range(f"O{prod_row}:R{prod_row}","Thủ trưởng đơn vị",footer_font_size_title)

                prod_row +=1
                sheet.merge_range(f"A{prod_row}:C{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"D{prod_row}:F{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"G{prod_row}:J{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"K{prod_row}:N{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"O{prod_row}:R{prod_row}","(Ký, họ tên, đóng dấu)",footer_font_size_sign)

                prod_row = prod_row + 5
                sheet.merge_range(f"A{prod_row}:C{prod_row}",obj.voter_id.name_without_position if obj.voter_id else "",footer_font_size_title)
                sheet.merge_range(f"D{prod_row}:F{prod_row}",obj.lead_team_id.name_without_position if obj.lead_team_id else "",footer_font_size_title)
                sheet.merge_range(f"G{prod_row}:J{prod_row}",obj.lead_sale_id.name_without_position if obj.lead_sale_id else "",footer_font_size_title)
                sheet.merge_range(f"K{prod_row}:N{prod_row}",obj.chief_acc_id.name_without_position if obj.chief_acc_id else "",footer_font_size_title)
                sheet.merge_range(f"O{prod_row}:R{prod_row}",obj.unit_heads_id.name_without_position if obj.unit_heads_id else "",footer_font_size_title)
            else:
                prod_row +=1
                sheet.merge_range(f"A{prod_row}:E{prod_row}","Người Lập Biểu",footer_font_size_title)
                sheet.merge_range(f"F{prod_row}:J{prod_row}","Kế Toán Trưởng",footer_font_size_title)
                sheet.merge_range(f"K{prod_row}:R{prod_row}","Thủ trưởng đơn vị",footer_font_size_title)

                prod_row +=1
                sheet.merge_range(f"A{prod_row}:E{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"F{prod_row}:J{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"K{prod_row}:R{prod_row}","(Ký, họ tên, đóng dấu)",footer_font_size_sign)

                prod_row = prod_row + 5
                sheet.merge_range(f"A{prod_row}:E{prod_row}",obj.voter_id.name_without_position if obj.voter_id else "", footer_font_size_title)
                sheet.merge_range(f"F{prod_row}:J{prod_row}",obj.chief_acc_id.name_without_position if obj.chief_acc_id else "", footer_font_size_title)
                sheet.merge_range(f"K{prod_row}:R{prod_row}",obj.unit_heads_id.name_without_position if obj.unit_heads_id else "",  footer_font_size_title)
