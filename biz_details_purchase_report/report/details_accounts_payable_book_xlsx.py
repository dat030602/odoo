# -*- coding: utf-8 -*-
from odoo import models, _
import base64
import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class DetailsAccountsPayableBookXlsx(models.AbstractModel):
    _name = 'report.biz_details_purchase_report.ac_payable_xlsx'
    _description = 'Chi Tiết Công Nợ Phải Trả (Excel)'
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
            signature_style = workbook.add_format({
                'italic': True, 'font_name': 'Times New Roman',
                'font_size': 12, 'valign': 'vcenter', 'align': 'center'
            })

            worksheet_name = _('Chi Tiết Công Nợ')
            sheet = workbook.add_worksheet(worksheet_name)
            sheet.set_landscape()

            is_out = o.partner_type == 'out'

            if is_out:
                col_widths = [5, 12, 12, 18, 12, 15, 12, 12, 25, 12, 12, 15, 15, 15, 15, 10]
            else:
                col_widths = [5, 15, 15, 18, 15, 30, 15, 15, 15, 15, 12]

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
                              get_format({'align': 'left', 'font_size': 15}))
            y_offset += 1

            # Tiêu đề
            sheet.merge_range(y_offset, 0, y_offset, total_cols,
                              'CHI TIẾT CÔNG NỢ PHẢI TRẢ', get_format(report_title))
            y_offset += 1

            from_date = o.convert_print(o.date_from)
            to_date = o.convert_print(o.date_to)
            
            sub_title = f"Từ ngày {from_date} đến ngày {to_date}"
            sheet.merge_range(y_offset, 0, y_offset, total_cols, sub_title, get_format(sub_title_format))
            y_offset += 1

            # Header
            header_fmt = get_format({'bold': True, 'align': 'center', 'border': 1, 'text_wrap': True})

            if is_out:
                sheet.merge_range(y_offset, 0, y_offset+1, 0, 'STT', header_fmt)
                sheet.merge_range(y_offset, 1, y_offset+1, 1, 'Mã NCC', header_fmt)
                sheet.merge_range(y_offset, 2, y_offset+1, 2, 'Ngày chứng từ', header_fmt)
                sheet.merge_range(y_offset, 3, y_offset+1, 3, 'Số chứng từ', header_fmt)
                sheet.merge_range(y_offset, 4, y_offset+1, 4, 'Ngày hóa đơn', header_fmt)
                sheet.merge_range(y_offset, 5, y_offset+1, 5, 'Số hóa đơn', header_fmt)
                sheet.merge_range(y_offset, 6, y_offset+1, 6, 'Số lượng', header_fmt)
                sheet.merge_range(y_offset, 7, y_offset+1, 7, 'Đơn giá', header_fmt)
                sheet.merge_range(y_offset, 8, y_offset+1, 8, 'Diễn giải', header_fmt)
                sheet.merge_range(y_offset, 9, y_offset+1, 9, 'TK công nợ', header_fmt)
                sheet.merge_range(y_offset, 10, y_offset+1, 10, 'TK đối ứng', header_fmt)
                
                sheet.merge_range(y_offset, 11, y_offset, 12, 'Phát sinh', header_fmt)
                sheet.write(y_offset+1, 11, 'Nợ', header_fmt)
                sheet.write(y_offset+1, 12, 'Có', header_fmt)
                
                sheet.merge_range(y_offset, 13, y_offset, 14, 'Số dư', header_fmt)
                sheet.write(y_offset+1, 13, 'Nợ', header_fmt)
                sheet.write(y_offset+1, 14, 'Có', header_fmt)
                
                sheet.merge_range(y_offset, 15, y_offset+1, 15, 'ĐVT', header_fmt)
            else:
                sheet.merge_range(y_offset, 0, y_offset+1, 0, 'STT', header_fmt)
                sheet.merge_range(y_offset, 1, y_offset+1, 1, 'Ngày hạch toán', header_fmt)
                sheet.merge_range(y_offset, 2, y_offset+1, 2, 'Ngày chứng từ', header_fmt)
                sheet.merge_range(y_offset, 3, y_offset+1, 3, 'Số chứng từ', header_fmt)
                sheet.merge_range(y_offset, 4, y_offset+1, 4, 'Số hóa đơn', header_fmt)
                sheet.merge_range(y_offset, 5, y_offset+1, 5, 'Diễn giải', header_fmt)
                
                sheet.merge_range(y_offset, 6, y_offset, 7, 'Phát sinh', header_fmt)
                sheet.write(y_offset+1, 6, 'Nợ', header_fmt)
                sheet.write(y_offset+1, 7, 'Có', header_fmt)
                
                sheet.merge_range(y_offset, 8, y_offset, 9, 'Số dư', header_fmt)
                sheet.write(y_offset+1, 8, 'Nợ', header_fmt)
                sheet.write(y_offset+1, 9, 'Có', header_fmt)
                
                sheet.merge_range(y_offset, 10, y_offset+1, 10, 'Số lượng', header_fmt)

            y_offset += 2

            # Body
            stt = 0
            
            num_fmt = get_format({'align': 'right', 'num_format': '#,##0', 'border': 1})
            txt_fmt = get_format({'align': 'left', 'border': 1})
            ctr_fmt = get_format({'align': 'center', 'border': 1})
            
            sum_qty = sum_debit = sum_credit = sum_end_debit = sum_end_credit = 0

            for line in o.line_ids:
                stt += 1
                sheet.write(y_offset, 0, stt, ctr_fmt)
                
                if is_out:
                    sheet.write(y_offset, 1,  line.partner_code or '', txt_fmt)
                    sheet.write(y_offset, 2,  o.convert_print(line.date) or '', ctr_fmt)
                    sheet.write(y_offset, 3,  line.move_id.name if line.move_id else '', ctr_fmt)
                    sheet.write(y_offset, 4,  o.convert_print(line.invoice_date) or '', ctr_fmt)
                    sheet.write(y_offset, 5,  line.reference or '', ctr_fmt)
                    sheet.write(y_offset, 6,  line.product_uom_qty or 0, num_fmt)
                    sheet.write(y_offset, 7,  line.price_unit or 0, num_fmt)
                    sheet.write(y_offset, 8,  line.note or '', txt_fmt)
                    sheet.write(y_offset, 9,  line.account_id.code if line.account_id else '', txt_fmt)
                    sheet.write(y_offset, 10, line.account_dest_id.code if line.account_dest_id else '', txt_fmt)
                    sheet.write(y_offset, 11, line.debit or 0, num_fmt)
                    sheet.write(y_offset, 12, line.credit or 0, num_fmt)
                    sheet.write(y_offset, 13, line.end_debit or 0, num_fmt)
                    sheet.write(y_offset, 14, line.end_credit or 0, num_fmt)
                    sheet.write(y_offset, 15, line.uom_id.name if line.uom_id else '', ctr_fmt)
                else:
                    sheet.write(y_offset, 1,  o.convert_print(line.invoice_date) or '', ctr_fmt)
                    sheet.write(y_offset, 2,  o.convert_print(line.date) or '', ctr_fmt)
                    sheet.write(y_offset, 3,  line.move_id.name if line.move_id else '', ctr_fmt)
                    sheet.write(y_offset, 4,  line.reference or '', ctr_fmt)
                    sheet.write(y_offset, 5,  line.note or '', txt_fmt)
                    sheet.write(y_offset, 6,  line.debit or 0, num_fmt)
                    sheet.write(y_offset, 7,  line.credit or 0, num_fmt)
                    sheet.write(y_offset, 8,  line.end_debit or 0, num_fmt)
                    sheet.write(y_offset, 9,  line.end_credit or 0, num_fmt)
                    sheet.write(y_offset, 10, line.product_uom_qty or 0, num_fmt)
                    
                sum_qty += line.product_uom_qty
                sum_debit += line.debit
                sum_credit += line.credit
                sum_end_debit += line.end_debit
                sum_end_credit += line.end_credit
                y_offset += 1

            # Tổng cộng
            total_fmt = get_format({'bold': True, 'align': 'left', 'border': 1})
            num_total_fmt = get_format({'bold': True, 'align': 'right', 'num_format': '#,##0', 'border': 1})
            empty_fmt = get_format({'border': 1})
            
            if is_out:
                sheet.merge_range(y_offset, 0, y_offset, 5, 'Tổng cộng', total_fmt)
                sheet.write(y_offset, 6, sum_qty, num_total_fmt)
                sheet.write(y_offset, 7, '', empty_fmt)
                sheet.write(y_offset, 8, '', empty_fmt)
                sheet.write(y_offset, 9, '', empty_fmt)
                sheet.write(y_offset, 10, '', empty_fmt)
                sheet.write(y_offset, 11, sum_debit, num_total_fmt)
                sheet.write(y_offset, 12, sum_credit, num_total_fmt)
                sheet.write(y_offset, 13, sum_end_debit, num_total_fmt)
                sheet.write(y_offset, 14, sum_end_credit, num_total_fmt)
                sheet.write(y_offset, 15, '', empty_fmt)
            else:
                sheet.merge_range(y_offset, 0, y_offset, 5, 'Tổng cộng', total_fmt)
                sheet.write(y_offset, 6, sum_debit, num_total_fmt)
                sheet.write(y_offset, 7, sum_credit, num_total_fmt)
                sheet.write(y_offset, 8, sum_end_debit, num_total_fmt)
                sheet.write(y_offset, 9, sum_end_credit, num_total_fmt)
                sheet.write(y_offset, 10, sum_qty, num_total_fmt)
            
            y_offset += 2

            # Ký tên
            now = datetime.now()
            date_str = f"Ngày {now.strftime('%d')} tháng {now.strftime('%m')} năm {now.strftime('%Y')}"
            
            if is_out:
                sheet.merge_range(y_offset, 11, y_offset, 15, date_str, get_format({'align': 'center', 'italic': True}))
            else:
                sheet.merge_range(y_offset, 6, y_offset, 10, date_str, get_format({'align': 'center', 'italic': True}))

            y_offset += 1

            roles = ['Người Lập Phiếu', 'Trưởng Phòng Thương Mại', 'Kế Toán Trưởng', 'Thủ Trưởng Đơn Vị']
            signers = [
                o.voter_id.name_without_position if o.voter_id else '',
                o.department_head_id.name_without_position if o.department_head_id else '',
                o.chief_accountant_id.name_without_position if o.chief_accountant_id else '',
                o.director_id.name_without_position if o.director_id else '',
            ]
            
            # Cấu hình signature images (nếu state là approved)
            signature_images = [
                o.voter_id.sign_signature if o.sudo().voter_id and o.state == 'approved' else False,
                o.department_head_id.sign_signature if o.sudo().department_head_id and o.state == 'approved' else False,
                o.chief_accountant_id.sign_signature if o.sudo().chief_accountant_id and o.state == 'approved' else False,
                o.director_id.sign_signature if o.sudo().director_id and o.state == 'approved' else False,
            ]
            
            if is_out:
                blocks = [(0, 3), (4, 7), (8, 11), (12, 15)]
                # Định vị cột chèn ảnh để nó nằm giữa block
                img_positions = [(1, 20), (5, 20), (9, 20), (13, 20)]
            else:
                blocks = [(0, 1), (2, 4), (5, 7), (8, 10)]
                img_positions = [(1, 0), (3, 20), (6, 10), (9, 10)]
                
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, roles[i],
                                  get_format({'bold': True, 'align': 'center'}))
            y_offset += 1
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, '(Ký, họ tên)', signature_style)
            y_offset += 1
            
            # Chêm rỗng để chèn ảnh chữ ký
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
                sheet.merge_range(y_offset, c_start, y_offset, c_end, signers[i],
                                  get_format({'bold': True, 'align': 'center'}))
