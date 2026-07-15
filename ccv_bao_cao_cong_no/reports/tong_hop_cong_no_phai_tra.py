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

class tong_hop_cong_no_phai_tra(models.AbstractModel):
    _name = "report.ccv_bao_cao_cong_no.tong_hop_cong_no_phai_tra"
    _inherit = "report.report_xlsx.abstract"
    _description = "Tong Hop Cong No Phai Tra"

    def get_data_export(self, obj):
        lines_obj = obj.line2_th_ids
        sum_start_credit = sum(lines_obj.mapped("start_credit"))
        sum_start_debit = sum(lines_obj.mapped("start_debit"))
        sum_ps_credit = sum(lines_obj.mapped("ps_credit"))
        sum_ps_debit = sum(lines_obj.mapped("ps_debit"))
        sum_end_credit = sum(lines_obj.mapped("end_credit"))
        sum_end_debit = sum(lines_obj.mapped("end_debit"))
        lines = []
        count = 1
        for data in lines_obj:
            customer_name = data.partner_name if data.partner_name else ""
            customer_code = data.partner_code if data.partner_code else ""
            address = data.address if data.address else ""
            vat = data.vat if data.vat else ""
            start_credit = data.start_credit
            start_debit = data.start_debit
            ps_credit = data.ps_credit
            ps_debit = data.ps_debit
            end_credit = data.end_credit
            end_debit = data.end_debit

            if (
                start_credit == 0
                and start_debit == 0
                and ps_credit == 0
                and ps_debit == 0
            ):
                continue

            vals = {
                "no": count,
                "customer_name": customer_name,
                "customer_code": customer_code,
                "address": address,
                "vat": vat,
                "start_credit": start_credit,
                "start_debit": start_debit,
                "ps_credit": ps_credit,
                "ps_debit": ps_debit,
                "end_credit": end_credit,
                "end_debit": end_debit,
            }
            count += 1
            lines.append(vals)
        return {
            "sum": {
                "sum_start_credit": sum_start_credit,
                "sum_start_debit": sum_start_debit,
                "sum_ps_credit": sum_ps_credit,
                "sum_ps_debit": sum_ps_debit,
                "sum_end_credit": sum_end_credit,
                "sum_end_debit": sum_end_debit,
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

            format_company_title = workbook.add_format(json_format(13))
            format_company_title.set_align("left")

            # Đầu đề
            sheet.merge_range("A4:K4","TỔNG HỢP CÔNG NỢ PHẢI TRẢ%s" % ((" %s" % tile_report.upper()) if tile_report else " "),format1)
            sheet.set_row(4, 35)
            sheet.set_row(5, 20)
            sheet.merge_range("A5:K5","Tài khoản: %s; Loại tiền: VND; Từ ngày %s đến ngày %s" % (account,date_start,date_end),format21)
            sheet.merge_range("C2:K2","Công ty TNHH Con Cò Vàng - Mã số thuế: 0305995751", format_company_title)
            sheet.insert_image('A1', get_module_resource('ccv_bao_cao_cong_no', 'static/src/img', 'logo.png'), {'x_offset': 0, 'y_offset': 0,"x_scale": 0.22, "y_scale": 0.22})

            # Bảng
            w_row_header = 6
            i = 0
            sheet.merge_range(f"A{w_row_header}:A{w_row_header+1}","STT",format_header)
            i += 1
            sheet.merge_range(f"B{w_row_header}:B{w_row_header+1}","Mã nhà cung cấp",format_header)
            i += 1
            sheet.merge_range(f"C{w_row_header}:C{w_row_header+1}","Tên nhà cung cấp",format_header)
            i += 1
            sheet.merge_range(f"D{w_row_header}:D{w_row_header+1}","Địa chỉ",format_header)
            i += 1
            sheet.merge_range(f"E{w_row_header}:E{w_row_header+1}","Mã số thuế",format_header)
            i += 1
            sheet.merge_range(f"F{w_row_header}:G{w_row_header}","Số dư đầu kỳ",format_header)
            sheet.write(w_row_header, i, "Nợ", format_header)
            sheet.write(w_row_header, i + 1, "Có", format_header)
            i += 2
            sheet.merge_range(f"H{w_row_header}:I{w_row_header}","Phát sinh",format_header)
            sheet.write(w_row_header, i, "Nợ", format_header)
            sheet.write(w_row_header, i + 1, "Có", format_header)
            i += 2
            sheet.merge_range(f"J{w_row_header}:K{w_row_header}","Số dư cuối kỳ",format_header)
            sheet.write(w_row_header, i, "Nợ", format_header)
            sheet.write(w_row_header, i + 1, "Có", format_header)

            prod_row = 7
            sum = data_raw['sum']
            for each in data_raw['lines']:
                prod_col = 0
                sheet.set_column(prod_col, prod_col, 5)
                sheet.write(prod_row, prod_col, each["no"], font_size_8)

                prod_col += 1
                sheet.set_column(prod_col, prod_col, 12)
                sheet.write(prod_row, prod_col, each["customer_code"], font_size_8)

                prod_col += 1
                sheet.set_column(prod_col, prod_col, 25)
                sheet.write(prod_row, prod_col, each["customer_name"], font_size_8)

                prod_col += 1
                sheet.set_column(prod_col, prod_col, 25)
                sheet.write(prod_row, prod_col, each["address"], font_size_8)

                prod_col += 1
                sheet.set_column(prod_col, prod_col, 15)
                sheet.write(prod_row, prod_col, each["vat"], font_size_8)

                prod_col += 1
                sheet.set_column(prod_col, prod_col, 10)
                sheet.write(prod_row, prod_col, each["start_debit"] if each["start_debit"] != 0.00 else "", font_size_8_number)

                prod_col += 1
                sheet.set_column(prod_col, prod_col, 10)
                sheet.write(prod_row, prod_col, each["start_credit"] if each["start_credit"] != 0.00 else "", font_size_8_number)

                prod_col += 1
                sheet.set_column(prod_col, prod_col, 10)
                sheet.write(prod_row, prod_col, each["ps_debit"] if each["ps_debit"] != 0.00 else "", font_size_8_number)

                prod_col += 1
                sheet.set_column(prod_col, prod_col, 10)
                sheet.write(prod_row, prod_col, each["ps_credit"] if each["ps_credit"] != 0.00 else "", font_size_8_number)

                prod_col += 1
                sheet.set_column(prod_col, prod_col, 10)
                sheet.write(prod_row, prod_col, each["end_debit"] if each["end_debit"] != 0.00 else "", font_size_8_number)

                prod_col += 1
                sheet.set_column(prod_col, prod_col, 10)
                sheet.write(prod_row, prod_col, each["end_credit"] if each["end_credit"] != 0.00 else "", font_size_8_number)

                prod_row +=1

            # Tổng cộng
            total_font_size = workbook.add_format(
                {
                    "bottom": True,
                    "top": True,
                    "right": True,
                    "left": True,
                    "font_size": 10,
                    "align": "vcenter",
                    "font_name": "Times New Roman",
                    "bold": True,
                }
            )
            total_font_size.set_align("right")
            total_font_size.set_text_wrap()
            total_font_size.set_num_format("#,##0")

            total_font_size_text = workbook.add_format(
                {
                    "bottom": True,
                    "top": True,
                    "right": True,
                    "left": True,
                    "font_size": 10,
                    "align": "vcenter",
                    "font_name": "Times New Roman",
                    "bold": True,
                }
            )
            total_font_size_text.set_text_wrap()
            total_font_size_text.set_align("left")

            prod_row += 1
            prod_col = 0
            sheet.merge_range(f"A{prod_row}:E{prod_row}","Tổng cộng",total_font_size_text)

            prod_row -= 1
            prod_col += 5
            sheet.write(prod_row, prod_col, sum["sum_start_debit"] if sum["sum_start_debit"] != 0.00 else "", total_font_size)

            prod_col +=1
            sheet.write(prod_row, prod_col, sum["sum_start_credit"] if sum["sum_start_credit"] != 0.00 else "", total_font_size)

            prod_col +=1
            sheet.write(prod_row, prod_col, sum["sum_ps_debit"] if sum["sum_ps_debit"] != 0.00 else "", total_font_size)

            prod_col +=1
            sheet.write(prod_row, prod_col, sum["sum_ps_credit"] if sum["sum_ps_credit"] != 0.00 else "", total_font_size)

            prod_col +=1
            sheet.write(prod_row, prod_col, sum["sum_end_debit"] if sum["sum_end_debit"] != 0.00 else "", total_font_size)

            prod_col +=1
            sheet.write(prod_row, prod_col, sum["sum_end_credit"] if sum["sum_end_credit"] != 0.00 else "", total_font_size)
            
            prod_row +=1

            # Footer
            # Format cho số
            footer_font_size_title = workbook.add_format(
                {
                    "bottom": False,
                    "top": False,
                    "right": False,
                    "left": False,
                    "font_size": 12,
                    "align": "vcenter",
                    "font_name": "Times New Roman",
                    "bold": True,
                }
            )
            footer_font_size_title.set_align("center")
            footer_font_size_title.set_text_wrap()

            footer_font_size_sign = workbook.add_format(
                {
                    "bottom": False,
                    "top": False,
                    "right": False,
                    "left": False,
                    "font_size": 11,
                    "align": "vcenter",
                    "font_name": "Times New Roman",
                    "italic": True,
                }
            )
            footer_font_size_sign.set_align("center")
            footer_font_size_sign.set_text_wrap()

            prod_row = prod_row + 2
            sheet.merge_range(f"I{prod_row}:K{prod_row}","Ngày ..... tháng ..... năm .........",footer_font_size_sign)

            if obj.is_sale:
                prod_row +=1
                sheet.merge_range(f"A{prod_row}:B{prod_row}","Người Lập Biểu",footer_font_size_title)
                sheet.merge_range(f"C{prod_row}:D{prod_row}","Trưởng khu vực",footer_font_size_title)
                sheet.merge_range(f"E{prod_row}:F{prod_row}","Phòng Kinh doanh",footer_font_size_title)
                sheet.merge_range(f"G{prod_row}:H{prod_row}","Kế toán trưởng",footer_font_size_title)
                sheet.merge_range(f"I{prod_row}:K{prod_row}","Thủ trưởng đơn vị",footer_font_size_title)

                prod_row +=1
                sheet.merge_range(f"A{prod_row}:B{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"C{prod_row}:D{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"E{prod_row}:F{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"G{prod_row}:H{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"I{prod_row}:K{prod_row}","(Ký, họ tên, đóng dấu)",footer_font_size_sign)

                prod_row = prod_row + 5
                sheet.merge_range(f"A{prod_row}:B{prod_row}",obj.voter_id.name_without_position if obj.voter_id else "",footer_font_size_title)
                sheet.merge_range(f"C{prod_row}:D{prod_row}",obj.lead_team_id.name_without_position if obj.lead_team_id else "",footer_font_size_title)
                sheet.merge_range(f"E{prod_row}:F{prod_row}",obj.lead_sale_id.name_without_position if obj.lead_sale_id else "",footer_font_size_title)
                sheet.merge_range(f"G{prod_row}:H{prod_row}",obj.chief_acc_id.name_without_position if obj.chief_acc_id else "",footer_font_size_title)
                sheet.merge_range(f"I{prod_row}:K{prod_row}",obj.unit_heads_id.name_without_position if obj.unit_heads_id else "",footer_font_size_title)
            else:
                prod_row +=1
                sheet.merge_range(f"A{prod_row}:C{prod_row}","Người Lập Biểu",footer_font_size_title)
                sheet.merge_range(f"D{prod_row}:F{prod_row}","Kế Toán Trưởng",footer_font_size_title)
                sheet.merge_range(f"G{prod_row}:K{prod_row}","Thủ trưởng đơn vị",footer_font_size_title)

                prod_row +=1
                sheet.merge_range(f"A{prod_row}:C{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"D{prod_row}:F{prod_row}","(Ký, họ tên)",footer_font_size_sign)
                sheet.merge_range(f"G{prod_row}:K{prod_row}","(Ký, họ tên, đóng dấu)",footer_font_size_sign)

                prod_row = prod_row + 5
                sheet.merge_range(f"A{prod_row}:C{prod_row}",obj.voter_id.name_without_position if obj.voter_id else "", footer_font_size_title)
                sheet.merge_range(f"D{prod_row}:F{prod_row}",obj.chief_acc_id.name_without_position if obj.chief_acc_id else "", footer_font_size_title)
                sheet.merge_range(f"G{prod_row}:K{prod_row}",obj.unit_heads_id.name_without_position if obj.unit_heads_id else "",  footer_font_size_title)

