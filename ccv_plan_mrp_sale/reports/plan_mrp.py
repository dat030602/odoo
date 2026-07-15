# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.modules.module import get_module_resource

import xlsxwriter
import logging

_logger = logging.getLogger(__name__)

def json_format(font_size, font_name="Times New Roman", align="vcenter", border=0, bold=False, italic=False, bg_color=False,num_format=''):
    return {
        "font_name": font_name,
        "font_size": font_size,
        "align": align,
        "border": border,
        "bold": bold,
        "bg_color": bg_color,
        "italic": italic,
        "num_format": num_format,
    }

class plan_sale_mrp(models.AbstractModel):
    _name = "report.ccv_plan_mrp_sale.plan_mrp"
    _inherit = "report.report_xlsx.abstract"
    _description = "Kế hoạch sản xuất"

    @api.model
    def get_data_export_w_id(self, data_id):
        data = self.env['ccv.mrp.plan.export'].browse(data_id)
        return self.get_data_export(data)  
    
    def get_data_export(self, data):
        rows = []

        plan_sale = self.env['ccv.sale.plan.export'].sudo().search([('type','=','summary'),('date','=',data.date),('state','=','locked')])
        for line in data.line_ids.sudo().sorted('partner_id'):
            cur_sales = plan_sale.line_ids.filtered(lambda l:l.product_id == line.product_id).sorted()
            qty_available_total = line.qty_available

            for cur_sale in cur_sales:
                if qty_available_total < 0:
                    qty_available_total = 0
                qty_delivery = cur_sale.qty_delivery if cur_sale.qty_delivery > 0 else 0
                cur_qty_mrp = qty_delivery - qty_available_total if qty_delivery > qty_available_total else 0
                rows.append({
                    'stt': 0,
                    'partner_id': cur_sale.partner_id.id,
                    'ngay_len_don': cur_sale.date.strftime('%d/%m/%Y') if cur_sale.date else '',
                    'ten_khach_hang': cur_sale.partner_id.name or '',
                    'don_hang': cur_sale.order_id.name or '',
                    'ma_tp': cur_sale.product_id.default_code or '',
                    'ten_hang': cur_sale.get_clean_name() if cur_sale.name else cur_sale.product_id.with_context(lang='vi_VN').name,
                    'kd_ban': qty_delivery,
                    'ton_kho': qty_delivery if qty_available_total > qty_delivery else qty_available_total,
                    'san_xuat': cur_qty_mrp if cur_qty_mrp > 0 else 0,
                    'nmsx': line.picking_type_id.factory_name if line.picking_type_id and cur_qty_mrp > 0 else "",
                    'in_tem_phu': cur_sale.secondary_label_id.name if cur_sale.secondary_label_id else "",
                    'ghi_chu': cur_sale.note or '',
                    'kv': cur_sale.team_id.code or '',
                })
                qty_available_total -= cur_sale.qty_delivery
        if rows:
            rows = sorted(rows, key=lambda x: x['partner_id'])
            for idx, row in enumerate(rows, start=1):
                row['stt'] = idx
        return rows

    def generate_xlsx_report(self, workbook:xlsxwriter.Workbook, data, objects):
        for obj in objects.sudo():
            worksheet = workbook.add_worksheet('Kế hoạch sản xuất')
            worksheet.set_landscape()
            worksheet.set_paper(9)
            worksheet.set_margins(left=0.1, right=0.1, top=0.1, bottom=0.1)
            worksheet.freeze_panes(2,0)
            data_raw = self.get_data_export(obj)

            headers = ['STT','Ngày lên Đơn','Khách hàng','Đơn hàng','Mã TP','Tên hàng','KD bán','Tồn kho','Sản xuất','NMSX','In tem phụ','Ghi chú','KV']

            title_format = workbook.add_format(json_format(font_size=16,bold=True))
            title_format.set_align("center")

            bold = workbook.add_format(json_format(font_size=12,bold=True,border=1,bg_color='#D7E4BC'))
            bold.set_align("center")
            bold.set_text_wrap()
            
            bold_sum = workbook.add_format(json_format(font_size=11,bold=True,border=1))
            bold_sum.set_align("center")
            bold_sum.set_text_wrap()

            left_format = workbook.add_format(json_format(font_size=11,border=1))
            left_format.set_align("left")
            left_format.set_text_wrap()

            center_format = workbook.add_format(json_format(font_size=11,border=1))
            center_format.set_align("center")
            center_format.set_text_wrap()

            float_format = workbook.add_format(json_format(font_size=10,border=1,num_format='#,##0.000'))
            float_format.set_align("center")
            float_format.set_text_wrap()

            sum_format = workbook.add_format(json_format(font_size=10,bold=True,border=1,num_format='#,##0.000'))
            sum_format.set_align("center")
            sum_format.set_text_wrap()

            # Tiêu đề duy nhất
            export_date_str = obj.date.strftime('%d/%m/%Y') if obj.date else ''
            worksheet.merge_range('A1:M1', f'KẾ HOẠCH SẢN XUẤT NGÀY {export_date_str}', title_format)
            worksheet.set_row(0, 30)

            # Header cột
            for col_num, header in enumerate(headers):
                worksheet.write(1, col_num, header, bold)

            row = 2

            # Xuất dữ liệu
            for record in data_raw:
                worksheet.write(row, 0, record['stt'], center_format)
                worksheet.write(row, 1, record['ngay_len_don'], center_format)
                worksheet.write(row, 2, record['ten_khach_hang'], left_format)
                worksheet.write(row, 3, record['don_hang'], center_format)
                worksheet.write(row, 4, record['ma_tp'], left_format)
                worksheet.write(row, 5, record['ten_hang'], left_format)
                worksheet.write(row, 6, record['kd_ban'], float_format)
                worksheet.write(row, 7, record['ton_kho'], float_format)
                worksheet.write(row, 8, record['san_xuat'] if record['san_xuat'] else "", float_format)
                worksheet.write(row, 9, record['nmsx'], center_format)
                worksheet.write(row, 10, record['in_tem_phu'], center_format)
                worksheet.write(row, 11, record['ghi_chu'], left_format)
                worksheet.write(row, 12, record['kv'], center_format)
                row += 1

            # Dòng tổng cộng
            if data_raw:
                total_kd_ban = sum(record['kd_ban'] for record in data_raw if record['kd_ban'])
                total_ton_kho = sum(record['ton_kho'] for record in data_raw if record['ton_kho'])
                total_san_xuat = sum(record['san_xuat'] for record in data_raw if record['san_xuat'])

                worksheet.merge_range(f'A{row+1}:F{row+1}', 'TỔNG CỘNG', bold_sum)
                worksheet.write(row, 6, total_kd_ban, sum_format)
                worksheet.write(row, 7, total_ton_kho, sum_format)
                worksheet.write(row, 8, total_san_xuat, sum_format)

                # Các cột còn lại giữ border
                for col_num in range(9, 13):
                    worksheet.write(row, col_num, '', sum_format)

            # Set width cột
            size_headers = [5,15,20,15,15,20,10,10,10,15,15,15,10]
            for col_num in range(len(headers)):
                worksheet.set_column(col_num, col_num, size_headers[col_num])
            
            worksheet.autofilter(1, 0, row, len(size_headers) - 1)
