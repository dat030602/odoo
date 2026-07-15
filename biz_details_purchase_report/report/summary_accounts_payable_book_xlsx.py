# -*- coding: utf-8 -*-
from odoo import models, _
import base64
import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class SummaryAccountsPayableBookXlsx(models.AbstractModel):
    _name = 'report.biz_details_purchase_report.summary_ac_payable_xlsx'
    _description = 'Tổng Hợp Công Nợ Phải Trả (Excel)'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, docs):
        self = self.with_context(lang=self.env.user.lang)
        for o in docs:
            company_id = self.env.company

            def get_format(*arguments):
                normal_style = {'font_name': 'Times New Roman', 'font_size': 12, 'valign': 'vcenter', 'align': 'left'}
                for arg in arguments:
                    normal_style.update(arg)
                return workbook.add_format(normal_style)

            report_title = {'bold': True, 'font_size': 16, 'text_wrap': True, 'align': 'center'}
            sub_title_format = {'font_size': 13, 'text_wrap': True, 'align': 'center', 'bold': True}
            
            worksheet_name = _('Tổng Hợp Công Nợ Phải Trả')
            sheet = workbook.add_worksheet(worksheet_name)
            sheet.set_landscape()

            col_widths = [5, 15, 30, 40, 20, 20, 20, 20, 20, 20]
            for i, w in enumerate(col_widths):
                sheet.set_column(i, i, w)

            total_cols = len(col_widths) - 1

            y_offset = 0
            # Logo & company
            image = company_id.logo or False
            sheet.set_row(y_offset, 55)
            if image:
                image_data = io.BytesIO(base64.b64decode(image))
                sheet.insert_image(y_offset, 0, 'logo.png', {
                    'image_data': image_data, 'x_scale': 0.2, 'y_scale': 0.2,
                    'x_offset': 0, 'y_offset': 0
                })
            sheet.merge_range(y_offset, 0, y_offset, total_cols,
                              '                   ' + company_id.name + ' - Mã số thuế: ' + (company_id.vat or ''),
                              get_format({'bold': True, 'font_size': 13, 'valign': 'top'}))
            
            y_offset += 1
            sheet.merge_range(y_offset, 0, y_offset, total_cols,
                              '                   ' + 'Địa chỉ: ' + (company_id.street or ''),
                              get_format({'font_size': 13, 'valign': 'top'}))
            
            y_offset += 2
            sheet.merge_range(y_offset, 0, y_offset, total_cols, 'TỔNG HỢP CÔNG NỢ PHẢI TRẢ', get_format(report_title))
            
            y_offset += 1
            date_str = 'Từ ngày %s đến ngày %s' % (
                o.date_from.strftime('%d/%m/%Y'),
                o.date_to.strftime('%d/%m/%Y')
            )
            sheet.merge_range(y_offset, 0, y_offset, total_cols, date_str, get_format(sub_title_format))

            y_offset += 2
            
            header_format = get_format({'bold': True, 'align': 'center', 'border': 1, 'text_wrap': True})
            num_format = get_format({'align': 'right', 'border': 1, 'num_format': '#,##0'})
            text_format = get_format({'align': 'left', 'border': 1, 'text_wrap': True})
            center_format = get_format({'align': 'center', 'border': 1})

            # Headers
            sheet.merge_range(y_offset, 0, y_offset + 1, 0, 'STT', header_format)
            sheet.merge_range(y_offset, 1, y_offset + 1, 1, 'Mã NCC', header_format)
            sheet.merge_range(y_offset, 2, y_offset + 1, 2, 'Tên NCC', header_format)
            sheet.merge_range(y_offset, 3, y_offset + 1, 3, 'Địa chỉ', header_format)
            sheet.merge_range(y_offset, 4, y_offset, 5, 'Đầu kỳ', header_format)
            sheet.merge_range(y_offset, 6, y_offset, 7, 'Phát sinh', header_format)
            sheet.merge_range(y_offset, 8, y_offset, 9, 'Cuối kỳ', header_format)
            
            y_offset += 1
            sheet.write(y_offset, 4, 'Nợ', header_format)
            sheet.write(y_offset, 5, 'Có', header_format)
            sheet.write(y_offset, 6, 'Nợ', header_format)
            sheet.write(y_offset, 7, 'Có', header_format)
            sheet.write(y_offset, 8, 'Nợ', header_format)
            sheet.write(y_offset, 9, 'Có', header_format)

            y_offset += 1
            stt = 1
            
            sum_start_debit = 0
            sum_start_credit = 0
            sum_ps_debit = 0
            sum_ps_credit = 0
            sum_end_debit = 0
            sum_end_credit = 0

            for line in o.line_ids:
                sheet.write(y_offset, 0, stt, center_format)
                sheet.write(y_offset, 1, line.customer_code or '', center_format)
                sheet.write(y_offset, 2, line.customer_name or '', text_format)
                sheet.write(y_offset, 3, line.address or '', text_format)
                sheet.write(y_offset, 4, line.start_debit or 0, num_format)
                sheet.write(y_offset, 5, line.start_credit or 0, num_format)
                sheet.write(y_offset, 6, line.ps_debit or 0, num_format)
                sheet.write(y_offset, 7, line.ps_credit or 0, num_format)
                sheet.write(y_offset, 8, line.end_debit or 0, num_format)
                sheet.write(y_offset, 9, line.end_credit or 0, num_format)
                
                sum_start_debit += line.start_debit
                sum_start_credit += line.start_credit
                sum_ps_debit += line.ps_debit
                sum_ps_credit += line.ps_credit
                sum_end_debit += line.end_debit
                sum_end_credit += line.end_credit

                y_offset += 1
                stt += 1

            sheet.merge_range(y_offset, 0, y_offset, 3, 'Cộng:', get_format({'bold': True, 'align': 'center', 'border': 1}))
            sheet.write(y_offset, 4, sum_start_debit, get_format({'bold': True, 'align': 'right', 'border': 1, 'num_format': '#,##0'}))
            sheet.write(y_offset, 5, sum_start_credit, get_format({'bold': True, 'align': 'right', 'border': 1, 'num_format': '#,##0'}))
            sheet.write(y_offset, 6, sum_ps_debit, get_format({'bold': True, 'align': 'right', 'border': 1, 'num_format': '#,##0'}))
            sheet.write(y_offset, 7, sum_ps_credit, get_format({'bold': True, 'align': 'right', 'border': 1, 'num_format': '#,##0'}))
            sheet.write(y_offset, 8, sum_end_debit, get_format({'bold': True, 'align': 'right', 'border': 1, 'num_format': '#,##0'}))
            sheet.write(y_offset, 9, sum_end_credit, get_format({'bold': True, 'align': 'right', 'border': 1, 'num_format': '#,##0'}))

            # Ký duyệt
            y_offset += 2
            date_today = datetime.now()
            date_str_footer = 'Ngày %s tháng %s năm %s' % (
                str(date_today.day).zfill(2),
                str(date_today.month).zfill(2),
                date_today.year
            )
            sheet.merge_range(y_offset, total_cols - 2, y_offset, total_cols, date_str_footer, get_format({'italic': True, 'align': 'center'}))
            
            y_offset += 1
            
            roles = ['Người Lập Phiếu', 'Trưởng Phòng Thương Mại', 'Kế Toán Trưởng', 'Thủ Trưởng Đơn Vị']
            signers = [
                o.voter_id.name_without_position if o.voter_id else '',
                o.department_head_id.name_without_position if o.department_head_id else '',
                o.chief_accountant_id.name_without_position if o.chief_accountant_id else '',
                o.director_id.name_without_position if o.director_id else '',
            ]
            
            signature_images = [
                o.voter_id.sign_signature if o.sudo().voter_id and o.state == 'approved' else False,
                o.department_head_id.sign_signature if o.sudo().department_head_id and o.state == 'approved' else False,
                o.chief_accountant_id.sign_signature if o.sudo().chief_accountant_id and o.state == 'approved' else False,
                o.director_id.sign_signature if o.sudo().director_id and o.state == 'approved' else False,
            ]
            
            blocks = [(0, 1), (2, 3), (4, 6), (7, 8)]
            img_positions = [(0, 30), (2, 30), (5, 0), (7, 20)]
            
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, roles[i], get_format({'bold': True, 'align': 'center'}))
            y_offset += 1
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, '(Ký, họ tên)', get_format({'italic': True, 'align': 'center'}))
            y_offset += 1
            
            sheet.set_row(y_offset, 50)
            for i, (c_start, c_end) in enumerate(blocks):
                if signature_images[i]:
                    img_data = io.BytesIO(base64.b64decode(signature_images[i]))
                    c_img, x_offset = img_positions[i]
                    sheet.insert_image(y_offset, c_img, f'sign_{i}.png', {
                        'image_data': img_data, 'x_scale': 0.15, 'y_scale': 0.15,
                        'x_offset': x_offset, 'y_offset': 5
                    })
            y_offset += 1
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, signers[i], get_format({'bold': True, 'align': 'center'}))
