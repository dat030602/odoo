# -*- coding: utf-8 -*-
from odoo import models, _
import base64
import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class TongHopCongNoPhaiThuXlsx(models.AbstractModel):
    _name = 'report.ccv_sql.tong_hop_cong_no_phai_thu_xlsx'
    _description = 'Tổng hợp công nợ phải thu (Excel)'
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

            report_title_fmt = get_format({'bold': True, 'font_size': 16, 'text_wrap': True, 'align': 'center'})
            sub_title_fmt = get_format({'font_size': 13, 'text_wrap': True, 'align': 'center', 'bold': True, 'italic': True})
            header_fmt = get_format({'bold': True, 'align': 'center', 'border': 1, 'text_wrap': True, 'bg_color': '#D3E4F5'})
            signature_fmt = get_format({'italic': True, 'align': 'center'})

            # Cột: STT, Mã KH, Tên KH, Nhóm KH, Nợ đầu, Có đầu, PS Nợ, PS Có, Nợ cuối, Có cuối, Ghi chú
            col_widths = [5, 15, 30, 15, 18, 18, 18, 18, 18, 18, 20]
            total_cols = len(col_widths) - 1  # index cuối = 10

            sheet = workbook.add_worksheet('Tổng hợp công nợ phải thu')
            sheet.set_landscape()
            for i, w in enumerate(col_widths):
                sheet.set_column(i, i, w)

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

            # Tiêu đề chính
            sheet.merge_range(y_offset, 0, y_offset, total_cols, (o.name or 'BẢNG TỔNG HỢP CÔNG NỢ PHẢI THU').upper(), report_title_fmt)
            y_offset += 1

            # Phụ đề
            from_date = o.date_from.strftime('%d/%m/%Y') if o.date_from else ''
            to_date = o.date_to.strftime('%d/%m/%Y') if o.date_to else ''
            sub_title = f'Từ ngày {from_date} đến ngày {to_date}'
            sheet.merge_range(y_offset, 0, y_offset, total_cols, sub_title, sub_title_fmt)
            y_offset += 1

            # Header bảng
            headers = [
                'STT', 'Mã KH', 'Tên khách hàng', 'Nhóm KH',
                'Nợ đầu kỳ', 'Có đầu kỳ',
                'PS Nợ', 'PS Có',
                'Nợ cuối kỳ', 'Có cuối kỳ',
                'Ghi chú'
            ]
            for i, h in enumerate(headers):
                sheet.write(y_offset, i, h, header_fmt)
            y_offset += 1

            # Body
            stt = 0
            totals = {
                'start_debit': 0, 'start_credit': 0,
                'ps_debit': 0, 'ps_credit': 0,
                'end_debit': 0, 'end_credit': 0,
            }
            team_totals = {
                'start_debit': 0, 'start_credit': 0,
                'ps_debit': 0, 'ps_credit': 0,
                'end_debit': 0, 'end_credit': 0,
            }

            num_fmt       = get_format({'align': 'right', 'num_format': '#,##0', 'border': 1})
            txt_fmt       = get_format({'align': 'left', 'border': 1})
            ctr_fmt       = get_format({'align': 'center', 'border': 1})
            team_hdr_fmt  = get_format({'bold': True, 'align': 'left', 'border': 1, 'bg_color': '#F2F2F2'})
            sub_total_lbl = get_format({'bold': True, 'italic': True, 'align': 'center', 'border': 1, 'bg_color': '#DCE6F1'})
            sub_total_num = get_format({'bold': True, 'italic': True, 'align': 'right', 'num_format': '#,##0', 'border': 1, 'bg_color': '#DCE6F1'})
            sub_total_emp = get_format({'border': 1, 'bg_color': '#DCE6F1'})
            total_label_fmt = get_format({'bold': True, 'align': 'center', 'border': 1})
            num_total_fmt   = get_format({'bold': True, 'align': 'right', 'num_format': '#,##0', 'border': 1})
            empty_fmt       = get_format({'border': 1})

            current_team_id = None

            def write_team_subtotal(row, team_totals):
                sheet.merge_range(row, 0, row, 3, 'Tổng khu vực', sub_total_lbl)
                sheet.write(row, 4,  team_totals['start_debit'],  sub_total_num)
                sheet.write(row, 5,  team_totals['start_credit'], sub_total_num)
                sheet.write(row, 6,  team_totals['ps_debit'],     sub_total_num)
                sheet.write(row, 7,  team_totals['ps_credit'],    sub_total_num)
                sheet.write(row, 8,  team_totals['end_debit'],    sub_total_num)
                sheet.write(row, 9,  team_totals['end_credit'],   sub_total_num)
                sheet.write(row, 10, '', sub_total_emp)

            for line in o.line_ids:
                # Khi sang team mới
                if line.team_id.id != current_team_id:
                    # In dòng tổng team cũ (nếu đã có ít nhất 1 team)
                    if current_team_id is not None and any(team_totals.values()):
                        write_team_subtotal(y_offset, team_totals)
                        y_offset += 1
                        # Reset tổng team
                        team_totals = {k: 0 for k in team_totals}

                    current_team_id = line.team_id.id

                    # In tiêu đề tên team
                    if line.team_id:
                        sheet.merge_range(y_offset, 0, y_offset, total_cols,
                                          line.team_id.name, team_hdr_fmt)
                        y_offset += 1

                stt += 1
                sheet.write(y_offset, 0,  stt, ctr_fmt)
                sheet.write(y_offset, 1,  line.customer_code or '', ctr_fmt)
                sheet.write(y_offset, 2,  line.customer_name or (line.partner_id.name or ''), txt_fmt)
                sheet.write(y_offset, 3,  line.customer_group or '', ctr_fmt)
                sheet.write(y_offset, 4,  line.start_debit, num_fmt)
                sheet.write(y_offset, 5,  line.start_credit, num_fmt)
                sheet.write(y_offset, 6,  line.ps_debit, num_fmt)
                sheet.write(y_offset, 7,  line.ps_credit, num_fmt)
                sheet.write(y_offset, 8,  line.end_debit, num_fmt)
                sheet.write(y_offset, 9,  line.end_credit, num_fmt)
                sheet.write(y_offset, 10, line.note or '', txt_fmt)
                y_offset += 1

                for key in team_totals:
                    team_totals[key] += getattr(line, key)
                for key in totals:
                    totals[key] += getattr(line, key)

            # Dòng tổng team cuối cùng
            if o.line_ids and o.line_ids[-1].team_id and any(team_totals.values()):
                write_team_subtotal(y_offset, team_totals)
                y_offset += 1

            # Tổng cộng
            sheet.merge_range(y_offset, 0, y_offset, 3, 'TỔNG CỘNG', total_label_fmt)
            sheet.write(y_offset, 4,  totals['start_debit'],  num_total_fmt)
            sheet.write(y_offset, 5,  totals['start_credit'], num_total_fmt)
            sheet.write(y_offset, 6,  totals['ps_debit'],     num_total_fmt)
            sheet.write(y_offset, 7,  totals['ps_credit'],    num_total_fmt)
            sheet.write(y_offset, 8,  totals['end_debit'],    num_total_fmt)
            sheet.write(y_offset, 9,  totals['end_credit'],   num_total_fmt)
            sheet.write(y_offset, 10, '', empty_fmt)
            y_offset += 2


            # Ký tên
            now = datetime.now()
            date_str = f"Ngày {now.strftime('%d')} tháng {now.strftime('%m')} năm {now.strftime('%Y')}"
            sheet.merge_range(y_offset, 7, y_offset, total_cols, date_str,
                              get_format({'align': 'center', 'italic': True}))
            y_offset += 1

            roles = ['Lập Phiếu', 'Trưởng bộ phận', 'Kế toán tổng hợp', 'Kế Toán Trưởng', 'Thủ trưởng đơn vị']
            signers = [
                o.voter_id.name if o.voter_id else '',
                o.chief_dept_id.name if o.chief_dept_id else '',
                o.debt_accountant_id.name if o.debt_accountant_id else '',
                o.chief_acc_id.name if o.chief_acc_id else '',
                o.unit_heads_id.name if o.unit_heads_id else '',
            ]
            # Chia 11 cột cho 5 khối (0-1, 2-3, 4-5, 6-8, 9-10)
            blocks = [(0, 1), (2, 3), (4, 5), (6, 8), (9, 10)]
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, roles[i],
                                  get_format({'bold': True, 'align': 'center'}))
            y_offset += 1
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, '(Ký, họ tên)', signature_fmt)
            y_offset += 5
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, signers[i],
                                  get_format({'bold': True, 'align': 'center'}))
