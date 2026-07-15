# -*- coding: utf-8 -*-
from odoo import models, _
import base64
import io
import logging

_logger = logging.getLogger(__name__)


class DetailsPurchaseBookXlsx(models.AbstractModel):
    _name = 'report.biz_details_purchase_report.details_purchase_book_xlsx'
    _description = 'Details Purchase Book Xlsx'
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
            signature_style = workbook.add_format({'italic': True, 'font_name': 'Times New Roman', 'font_size': 12, 'valign': 'vcenter', 'align': 'center'})

            worksheet_name = _("Sổ chi tiết mua hàng")
            sheet = workbook.add_worksheet(worksheet_name)

            sheet.set_column(0, 0, 5)
            sheet.set_column(1, 2, 10)
            sheet.set_column(3, 3, 25)
            sheet.set_column(4, 4, 15)
            sheet.set_column(5, 6, 15)
            sheet.set_column(7, 8, 8)
            sheet.set_column(9, 9, 10)
            sheet.set_column(10, 10, 10)
            sheet.set_column(11, 12, 10)
            sheet.set_column(13, 16, 10)

            y_offset = 0
            image = company_id.logo or False
            sheet.set_row(y_offset, 55)
            if image:
                image_data = io.BytesIO(base64.b64decode(image))
                sheet.insert_image(y_offset, 0, image, {'image_data': image_data, 'x_scale': 0.2, 'y_scale': 0.2, 'x_offset': 0, 'y_offset': 0})
                sheet.merge_range(y_offset, 0, y_offset, 6, '                   ' + company_id.name + ' - Mã số thuế:' + company_id.vat, get_format({'align': 'left', 'font_size': 15, 'left': 10}))
            y_offset += 1
            sheet.merge_range(y_offset, 0, y_offset, 16, "SỔ CHI TIẾT MUA HÀNG", get_format(report_title))
            y_offset += 1
            from_date = o.date_from.strftime('%d/%m/%Y') if o.date_from else ''
            to_date = o.date_to.strftime('%d/%m/%Y') if o.date_to else ''
            sub_title = 'Từ ngày %s đến ngày %s' % (from_date, to_date)
            sheet.merge_range(y_offset, 0, y_offset, 16, sub_title, get_format(sub_title_format, {'italic': True}))
            y_offset += 1

            headers = ['STT', 'Ngày chứng từ', 'Số chứng từ', 'Tên nhà cung cấp', 'Mã hàng', 'Tên hàng', 'ĐVT',
                       'Số lượng mua', 'Tỷ giá', 'Đơn giá NT', 'Đơn giá', 'Giá trị mua NT', 'Giá trị mua',
                       'Mã kho', 'TK Nợ', 'TK Có', 'Đơn mua hàng']
            for i, h in enumerate(headers):
                sheet.write(y_offset, i, h, get_format({'bold': True, 'align': 'center'}))
            y_offset += 1

            stt = 0
            sum_quantity = 0
            sum_purchase_value_nt = 0
            sum_purchase_value = 0
            for line in o.line_ids:
                stt += 1
                sheet.write(y_offset, 0, stt, get_format({'align': 'center'}))
                sheet.write(y_offset, 1, line.date.strftime('%d/%m/%Y') if line.date else '', get_format({'align': 'center'}))
                sheet.write(y_offset, 2, line.name, get_format({'align': 'left', 'color': '#0000FF'}))
                sheet.write(y_offset, 3, line.partner_name, get_format({'align': 'left'}))
                sheet.write(y_offset, 4, line.product_code, get_format({'align': 'left'}))
                sheet.write(y_offset, 5, line.product_name, get_format({'align': 'left'}))
                sheet.write(y_offset, 6, line.product_uom_id, get_format({'align': 'left'}))
                sheet.write(y_offset, 7, line.quantity, get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 8, line.exchange_rate, get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 9, line.unit_price_nt, get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 10, line.unit_price, get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 11, line.purchase_value_nt, get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 12, line.purchase_value, get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 13, line.location_dest_id, get_format({'align': 'left'}))
                sheet.write(y_offset, 14, line.account_debit, get_format({'align': 'left'}))
                sheet.write(y_offset, 15, line.account_credit, get_format({'align': 'left'}))
                sheet.write(y_offset, 16, line.order_name, get_format({'align': 'left'}))
                y_offset += 1
                sum_quantity += line.quantity
                sum_purchase_value_nt += line.purchase_value_nt
                sum_purchase_value += line.purchase_value

            sheet.merge_range(y_offset, 0, y_offset, 6, 'Tổng cộng', get_format({'align': 'left', 'bold': True}))
            sheet.write(y_offset, 7, self.format_float_number(sum_quantity), get_format({'align': 'right', 'bold': True}))
            sheet.write(y_offset, 8, '', get_format())
            sheet.write(y_offset, 9, '', get_format())
            sheet.write(y_offset, 10, '', get_format())
            sheet.write(y_offset, 11, self.format_float_number(sum_purchase_value_nt), get_format({'align': 'right', 'bold': True}))
            sheet.write(y_offset, 12, self.format_float_number(sum_purchase_value), get_format({'align': 'right', 'bold': True}))
            sheet.write(y_offset, 13, '', get_format())
            sheet.write(y_offset, 14, '', get_format())
            sheet.write(y_offset, 15, '', get_format())
            sheet.write(y_offset, 16, '', get_format())
            y_offset += 2

            from datetime import datetime
            now = datetime.now()
            date_str = f"Đồng Nai, ngày {now.strftime('%d')} tháng {now.strftime('%m')} năm {now.strftime('%Y')}"
            sheet.merge_range(y_offset, 14, y_offset, 16, date_str, get_format({'align': 'center', 'italic': True}))
            y_offset += 1
            sheet.merge_range(y_offset, 0, y_offset, 2, 'Người lập biểu', get_format({'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 3, y_offset, 6, 'Phòng thương mại', get_format({'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 7, y_offset, 10, 'Phòng kế toán', get_format({'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 11, y_offset, 13, 'Kế toán trưởng', get_format({'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 14, y_offset, 16, 'Thủ trưởng đơn vị', get_format({'bold': True, 'align': 'center'}))
            y_offset += 1
            
            # Signatures images (only if approved)
            if o.state == 'approved':
                # Creator
                if o.creator_id.sign_signature:
                    img_data = io.BytesIO(base64.b64decode(o.creator_id.sign_signature))
                    sheet.insert_image(y_offset, 1, 'creator_sign.png', {'image_data': img_data, 'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 5})
                # Commercial
                if o.commercial_department_id.sign_signature:
                    img_data = io.BytesIO(base64.b64decode(o.commercial_department_id.sign_signature))
                    sheet.insert_image(y_offset, 4, 'comm_sign.png', {'image_data': img_data, 'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 5})
                # Accountant
                if o.accountant_id.sign_signature:
                    img_data = io.BytesIO(base64.b64decode(o.accountant_id.sign_signature))
                    sheet.insert_image(y_offset, 8, 'acc_sign.png', {'image_data': img_data, 'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 5})
                # Chief Accountant
                if o.accountant_chief_id.sign_signature:
                    img_data = io.BytesIO(base64.b64decode(o.accountant_chief_id.sign_signature))
                    sheet.insert_image(y_offset, 12, 'chief_acc_sign.png', {'image_data': img_data, 'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 5})
                # Unit Head
                if o.unit_head_id.sign_signature:
                    img_data = io.BytesIO(base64.b64decode(o.unit_head_id.sign_signature))
                    sheet.insert_image(y_offset, 15, 'unit_head_sign.png', {'image_data': img_data, 'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 5})
            
            y_offset += 5
            sheet.merge_range(y_offset, 0, y_offset, 2, o.creator_id.name_without_position or '', get_format({'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 3, y_offset, 6, o.commercial_department_id.name_without_position or '', get_format({'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 7, y_offset, 10, o.accountant_id.name_without_position or '', get_format({'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 11, y_offset, 13, o.accountant_chief_id.name_without_position or '', get_format({'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 14, y_offset, 16, o.unit_head_id.name_without_position or '', get_format({'bold': True, 'align': 'center'}))

    def format_float_number(self, num):
        if not num:
            return 0
        number = float(num)
        if number % 1 == 0:
            return "{:,.0f}".format(number)
        else:
            return "{:,.3f}".format(number)
