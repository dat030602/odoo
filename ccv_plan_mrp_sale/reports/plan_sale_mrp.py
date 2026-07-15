# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.modules.module import get_module_resource

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
    _name = "report.ccv_plan_mrp_sale.plan_sale_mrp"
    _inherit = "report.report_xlsx.abstract"
    _description = "Kế hoạch xuất hàng"  
    
    def get_data_export(self, data):
        rows = []
        stt = 1
        line_ids = data.line_ids.sudo()
        if data.is_next_plan:
            line_ids = self.env['ccv.sale.plan.export'].sudo().search([('type','=','team'),('date','=',data.date),('state','!=','draft')]).mapped('line_ids')
        for line in line_ids:
            qty_delivery = line.qty_delivery or 0
            rows.append({
                'stt': stt,
                'ngay_len_don': line.date.strftime('%d/%m/%Y') if line.date else '',
                'ten_khach_hang': line.partner_id.name or '',
                'don_hang': line.order_id.name or '',
                'ma_tp': line.product_id.default_code or '',
                'ten_hang': line.get_clean_name() if line.name else line.product_id.with_context(lang='vi_VN').name,
                'kd_ban': qty_delivery,
                'in_tem_phu': line.secondary_label_id.name if line.secondary_label_id else "",
                'ghi_chu': line.note or '',
                'kv': line.team_id.code or '',
            })
            stt += 1

        return rows

    def generate_xlsx_report(self, workbook, data, objects):
        for obj in objects.sudo():
            worksheet = workbook.add_worksheet('Kế hoạch xuất hàng')
            worksheet.set_landscape()
            worksheet.freeze_panes(2,0)
            data_raw = self.get_data_export(obj)

            headers = ['STT','Ngày lên Đơn','Khách hàng','Đơn hàng','Mã TP','Tên hàng','KD bán','In tem phụ','Ghi chú','KV']

            title_format = workbook.add_format({'bold': True,'font_size': 16,'align': 'center','valign': 'vcenter'})

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
            worksheet.merge_range('A1:J1', f'KẾ HOẠCH XUẤT HÀNG NGÀY {export_date_str}', title_format)
            worksheet.set_row(0, 30)

            # Header cột
            for col_num, header in enumerate(headers):
                worksheet.write(1, col_num, header, bold)

            row = 2

            for record in data_raw:
                worksheet.write(row, 0, record['stt'], center_format)
                worksheet.write(row, 1, record['ngay_len_don'], center_format)
                worksheet.write(row, 2, record['ten_khach_hang'], left_format)
                worksheet.write(row, 3, record['don_hang'], center_format)
                worksheet.write(row, 4, record['ma_tp'], left_format)
                worksheet.write(row, 5, record['ten_hang'], left_format)
                worksheet.write(row, 6, record['kd_ban'], float_format)
                worksheet.write(row, 7, record['in_tem_phu'], center_format)
                worksheet.write(row, 8, record['ghi_chu'], left_format)
                worksheet.write(row, 9, record['kv'], center_format)
                row += 1

            if data_raw:
                total_kd_ban = sum(record['kd_ban'] for record in data_raw if record['kd_ban'])
                worksheet.merge_range(f'A{row+1}:F{row+1}', 'TỔNG CỘNG', bold_sum)
                worksheet.write(row, 6, total_kd_ban, sum_format)
                for col_num in range(7, 10):
                    worksheet.write(row, col_num, '', sum_format)

            # Set width cột
            size_headers = [5,15,20,15,15,20,10,15,15,10]
            for col_num in range(len(headers)):
                worksheet.set_column(col_num, col_num, size_headers[col_num])
            
            worksheet.autofilter(1, 0, row, len(size_headers) - 1)
