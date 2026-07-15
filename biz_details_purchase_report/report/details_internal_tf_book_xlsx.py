# -*- coding: utf-8 -*-
from odoo import models, _
import base64
import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class DetailsInternalTfBookXlsx(models.AbstractModel):
    _name = 'report.biz_details_purchase_report.int_tf_xlsx'
    _description = 'Sổ chi tiết nhập hàng tại cảng (Excel)'
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
            sub_title_format = {'font_size': 13, 'text_wrap': True, 'align': 'center', 'bold': True, 'italic': True}
            signature_style = workbook.add_format({
                'italic': True, 'font_name': 'Times New Roman',
                'font_size': 12, 'valign': 'vcenter', 'align': 'center'
            })

            worksheet_name = _('Sổ chi tiết nhập hàng tại cảng')
            sheet = workbook.add_worksheet(worksheet_name)
            sheet.set_landscape()

            # Cột: STT, Ngày CT, Số CT, NCC, Mã hàng, Tên hàng, ĐVT, SL nhập, Tỷ giá,
            #       Đơn giá NT, Đơn giá, GT mua NT, GT mua, SL trả, GT trả NT, GT trả,
            #       Mã kho, TK Kho, TK ĐƯ, Đơn MH
            col_widths = [5, 12, 15, 25, 15, 25, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 15]
            for i, w in enumerate(col_widths):
                sheet.set_column(i, i, w)

            total_cols = len(col_widths) - 1  # index cuối

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
                              'SỔ CHI TIẾT NHẬP HÀNG TẠI CẢNG', get_format(report_title))
            y_offset += 1

            from_date = o.date_from.strftime('%d/%m/%Y') if o.date_from else ''
            to_date = o.date_to.strftime('%d/%m/%Y') if o.date_to else ''
            warehouse_names = ', '.join(o.warehouse_ids.mapped('name')) if o.warehouse_ids else 'Tất cả'
            sub_title = f'Kho: {warehouse_names}; Từ ngày {from_date} đến ngày {to_date}'
            sheet.merge_range(y_offset, 0, y_offset, total_cols, sub_title, get_format(sub_title_format))
            y_offset += 1

            # Header
            headers = [
                'STT', 'Ngày chứng từ', 'Số chứng từ', 'Tên nhà cung cấp', 'Mã hàng', 'Tên hàng', 'ĐVT',
                'Số lượng nhập', 'Tỷ giá', 'Đơn giá NT', 'Đơn giá',
                'Giá trị mua NT', 'Giá trị mua',
                'Số lượng trả lại', 'Giá trị trả lại NT', 'Giá trị trả lại',
                'Mã kho', 'TK Kho', 'TK Đối ứng', 'Đơn mua hàng'
            ]
            for i, h in enumerate(headers):
                sheet.write(y_offset, i, h, get_format({'bold': True, 'align': 'center', 'border': 1, 'text_wrap': True}))
            y_offset += 1

            # Body
            stt = 0
            totals = {
                'quantity': 0, 'amount_total_w_currency': 0, 'amount_total': 0,
                'return_quantity': 0, 'amount_total_return_w_currency': 0, 'amount_total_return': 0,
            }

            for line in o.line_ids:
                stt += 1
                num_fmt = get_format({'align': 'right', 'num_format': '#,##0.000', 'border': 1})
                txt_fmt = get_format({'align': 'left', 'border': 1})
                ctr_fmt = get_format({'align': 'center', 'border': 1})

                sheet.write(y_offset, 0,  stt, ctr_fmt)
                sheet.write(y_offset, 1,  line.date.strftime('%d/%m/%Y') if line.date else '', ctr_fmt)
                sheet.write(y_offset, 2,  line.name or '', get_format({'align': 'left', 'color': '#0000FF', 'border': 1}))
                sheet.write(y_offset, 3,  line.partner_name or '', txt_fmt)
                sheet.write(y_offset, 4,  line.product_code or '', txt_fmt)
                sheet.write(y_offset, 5,  line.product_name or '', txt_fmt)
                sheet.write(y_offset, 6,  line.uom_name or '', ctr_fmt)
                sheet.write(y_offset, 7,  line.quantity, num_fmt)
                sheet.write(y_offset, 8,  line.exchange_rate, num_fmt)
                sheet.write(y_offset, 9,  line.price_unit_w_currency, num_fmt)
                sheet.write(y_offset, 10, line.price_unit, num_fmt)
                sheet.write(y_offset, 11, line.amount_total_w_currency, num_fmt)
                sheet.write(y_offset, 12, line.amount_total, num_fmt)
                sheet.write(y_offset, 13, line.return_quantity, num_fmt)
                sheet.write(y_offset, 14, line.amount_total_return_w_currency, num_fmt)
                sheet.write(y_offset, 15, line.amount_total_return, num_fmt)
                sheet.write(y_offset, 16, line.warehouse_code or '', ctr_fmt)
                sheet.write(y_offset, 17, line.account or '', ctr_fmt)
                sheet.write(y_offset, 18, line.account_ctp or '', ctr_fmt)
                sheet.write(y_offset, 19, line.order_name or '', txt_fmt)
                y_offset += 1

                totals['quantity'] += line.quantity
                totals['amount_total_w_currency'] += line.amount_total_w_currency
                totals['amount_total'] += line.amount_total
                totals['return_quantity'] += line.return_quantity
                totals['amount_total_return_w_currency'] += line.amount_total_return_w_currency
                totals['amount_total_return'] += line.amount_total_return

            # Tổng cộng
            total_fmt = get_format({'bold': True, 'align': 'left', 'border': 1})
            num_total_fmt = get_format({'bold': True, 'align': 'right', 'num_format': '#,##0.000', 'border': 1})
            empty_fmt = get_format({'border': 1})
            sheet.merge_range(y_offset, 0, y_offset, 6, 'Tổng cộng', total_fmt)
            sheet.write(y_offset, 7,  totals['quantity'], num_total_fmt)
            sheet.write(y_offset, 8,  '', empty_fmt)
            sheet.write(y_offset, 9,  '', empty_fmt)
            sheet.write(y_offset, 10, '', empty_fmt)
            sheet.write(y_offset, 11, totals['amount_total_w_currency'], num_total_fmt)
            sheet.write(y_offset, 12, totals['amount_total'], num_total_fmt)
            sheet.write(y_offset, 13, totals['return_quantity'], num_total_fmt)
            sheet.write(y_offset, 14, totals['amount_total_return_w_currency'], num_total_fmt)
            sheet.write(y_offset, 15, totals['amount_total_return'], num_total_fmt)
            sheet.write(y_offset, 16, '', empty_fmt)
            sheet.write(y_offset, 17, '', empty_fmt)
            sheet.write(y_offset, 18, '', empty_fmt)
            sheet.write(y_offset, 19, '', empty_fmt)
            y_offset += 2

            # Ký tên
            now = datetime.now()
            date_str = f"Ngày {now.strftime('%d')} tháng {now.strftime('%m')} năm {now.strftime('%Y')}"
            sheet.merge_range(y_offset, 16, y_offset, total_cols, date_str,
                              get_format({'align': 'center', 'italic': True}))
            y_offset += 1

            roles = ['Người Lập', 'Phòng Thương mại', 'Phòng Kế toán', 'Thủ trưởng đơn vị']
            signers = [
                o.voter_id.name_without_position if o.voter_id else '',
                o.chief_trade_id.name_without_position if o.chief_trade_id else '',
                o.chief_finance_id.name_without_position if o.chief_finance_id else '',
                o.director_id.name_without_position if o.director_id else '',
            ]
            # Chia đều 20 cột cho 4 khối ký (mỗi khối 5 cột: 0-4, 5-9, 10-14, 15-19)
            blocks = [(0, 4), (5, 9), (10, 14), (15, 19)]
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, roles[i],
                                  get_format({'bold': True, 'align': 'center'}))
            y_offset += 1
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, '(Ký, họ tên)', signature_style)
            y_offset += 5
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, signers[i],
                                  get_format({'bold': True, 'align': 'center'}))
