# -*- coding: utf-8 -*-
from odoo import models, _
import base64
import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ChiTietCongNoPhaiThuXlsx(models.AbstractModel):
    _name = 'report.ccv_sql.chi_tiet_cong_no_phai_thu_xlsx'
    _description = 'Chi tiết công nợ phải thu (Excel)'
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

            # Cột: STT, Ngày, Số CT, Số HĐ, Diễn giải, TK đối, ĐVT, SL, Đơn giá, PS Nợ, PS Có, SD Nợ, SD Có, Mã hàng, Mã ĐH
            col_widths = [5, 12, 18, 15, 30, 10, 8, 12, 15, 15, 15, 15, 15, 15, 18]
            total_cols = len(col_widths) - 1 # 14

            sheet = workbook.add_worksheet('Chi tiết công nợ phải thu')
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
            sheet.merge_range(y_offset, 0, y_offset, total_cols, (o.name or 'BẢNG CHI TIẾT CÔNG NỢ PHẢI THU').upper(), report_title_fmt)
            y_offset += 1

            # Phụ đề
            from_date = o.date_from.strftime('%d/%m/%Y') if o.date_from else ''
            to_date = o.date_to.strftime('%d/%m/%Y') if o.date_to else ''
            sub_title = f'Từ ngày {from_date} đến ngày {to_date}'
            sheet.merge_range(y_offset, 0, y_offset, total_cols, sub_title, sub_title_fmt)
            y_offset += 1

            # Header bảng
            headers = [
                'STT', 'Ngày CT', 'Số CT', 'Số hóa đơn', 'Diễn giải',
                'TK đối ứng', 'ĐVT', 'Số lượng', 'Đơn giá',
                'PS Nợ', 'PS Có', 'SD Nợ', 'SD Có',
                'Mã hàng', 'Mã đơn hàng'
            ]
            for i, h in enumerate(headers):
                sheet.write(y_offset, i, h, header_fmt)
            y_offset += 1

            # Body
            num_fmt       = get_format({'align': 'right', 'num_format': '#,##0', 'border': 1})
            txt_fmt       = get_format({'align': 'left', 'border': 1})
            ctr_fmt       = get_format({'align': 'center', 'border': 1})
            team_hdr_fmt  = get_format({'bold': True, 'align': 'left', 'border': 1, 'bg_color': '#F2F2F2'})
            part_hdr_fmt  = get_format({'bold': True, 'align': 'left', 'border': 1, 'bg_color': '#FAFAFA'})
            sub_total_lbl = get_format({'bold': True, 'italic': True, 'align': 'center', 'border': 1, 'bg_color': '#DCE6F1'})
            sub_total_num = get_format({'bold': True, 'italic': True, 'align': 'right', 'num_format': '#,##0', 'border': 1, 'bg_color': '#DCE6F1'})
            sub_total_emp = get_format({'border': 1, 'bg_color': '#DCE6F1'})
            total_label_fmt = get_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#D3E4F5'})
            num_total_fmt   = get_format({'bold': True, 'align': 'right', 'num_format': '#,##0', 'border': 1, 'bg_color': '#D3E4F5'})
            empty_fmt       = get_format({'border': 1})

            # Logic Grouping
            current_team_id = None
            team_totals = {'qty': 0, 'debit': 0, 'credit': 0, 'end_debit': 0, 'end_credit': 0}
            grand_totals = {'qty': 0, 'debit': 0, 'credit': 0, 'end_debit': 0, 'end_credit': 0}

            def write_team_subtotal(row, totals, label):
                sheet.merge_range(row, 0, row, 6, label, sub_total_lbl)
                sheet.write(row, 7,  totals['qty'],        sub_total_num)
                sheet.write(row, 8,  '',                   sub_total_emp)
                sheet.write(row, 9,  totals['debit'],      sub_total_num)
                sheet.write(row, 10, totals['credit'],     sub_total_num)
                sheet.write(row, 11, totals['end_debit'],  sub_total_num)
                sheet.write(row, 12, totals['end_credit'], sub_total_num)
                sheet.write(row, 13, '',                   sub_total_emp)
                sheet.write(row, 14, '',                   sub_total_emp)

            # Lấy lines sorted
            lines = o.line_ids
            # Group lines by team then partner
            teams = lines.mapped('team_id') or [None]
            for team in teams:
                team_lines = lines.filtered(lambda l: l.team_id == team)
                if not team_lines: continue

                # Team Header
                if team:
                    sheet.merge_range(y_offset, 0, y_offset, total_cols, f"Đội bán hàng: {team.name}", team_hdr_fmt)
                    y_offset += 1
                
                t_totals = {'qty': 0, 'debit': 0, 'credit': 0, 'end_debit': 0, 'end_credit': 0}
                
                partners = team_lines.mapped('partner_id')
                for partner in partners:
                    p_lines = team_lines.filtered(lambda l: l.partner_id == partner)
                    if not p_lines: continue

                    # Partner Header
                    sheet.merge_range(y_offset, 0, y_offset, total_cols, f"   {partner.display_name}", part_hdr_fmt)
                    y_offset += 1

                    stt = 0
                    for line in p_lines:
                        stt += 1
                        sheet.write(y_offset, 0,  stt, ctr_fmt)
                        sheet.write(y_offset, 1,  line.date.strftime('%d/%m/%Y') if line.date else '', ctr_fmt)
                        sheet.write(y_offset, 2,  line.move_id.name or '', ctr_fmt)
                        sheet.write(y_offset, 3,  line.reference or '', ctr_fmt)
                        sheet.write(y_offset, 4,  line.note or '', txt_fmt)
                        sheet.write(y_offset, 5,  line.account_dest_id.code or '', ctr_fmt)
                        sheet.write(y_offset, 6,  line.uom_id.name or '', ctr_fmt)
                        sheet.write(y_offset, 7,  line.product_uom_qty, num_fmt)
                        sheet.write(y_offset, 8,  line.price_unit, num_fmt)
                        sheet.write(y_offset, 9,  line.debit, num_fmt)
                        sheet.write(y_offset, 10, line.credit, num_fmt)
                        sheet.write(y_offset, 11, line.end_debit, num_fmt)
                        sheet.write(y_offset, 12, line.end_credit, num_fmt)
                        sheet.write(y_offset, 13, line.default_code or '', txt_fmt)
                        sheet.write(y_offset, 14, line.order_id.name or '', ctr_fmt)
                        y_offset += 1

                    # Partner Subtotal
                    p_qty = sum(p_lines.mapped('product_uom_qty'))
                    p_deb = sum(p_lines.mapped('debit'))
                    p_cre = sum(p_lines.mapped('credit'))
                    p_end_deb = p_lines[-1].end_debit
                    p_end_cre = p_lines[-1].end_credit

                    sheet.merge_range(y_offset, 0, y_offset, 6, f"Tổng công nợ khách hàng: {partner.name}", get_format({'bold': True, 'border': 1}))
                    sheet.write(y_offset, 7,  p_qty,     num_total_fmt)
                    sheet.write(y_offset, 8,  '',        empty_fmt)
                    sheet.write(y_offset, 9,  p_deb,     num_total_fmt)
                    sheet.write(y_offset, 10, p_cre,     num_total_fmt)
                    sheet.write(y_offset, 11, p_end_deb, num_total_fmt)
                    sheet.write(y_offset, 12, p_end_cre, num_total_fmt)
                    sheet.write(y_offset, 13, '',        empty_fmt)
                    sheet.write(y_offset, 14, '',        empty_fmt)
                    y_offset += 1

                    t_totals['qty'] += p_qty
                    t_totals['debit'] += p_deb
                    t_totals['credit'] += p_cre
                    t_totals['end_debit'] += p_end_deb
                    t_totals['end_credit'] += p_end_cre

                # Team Subtotal
                if team:
                    write_team_subtotal(y_offset, t_totals, f"Tổng khu vực: {team.name}")
                    y_offset += 1

                grand_totals['qty'] += t_totals['qty']
                grand_totals['debit'] += t_totals['debit']
                grand_totals['credit'] += t_totals['credit']
                grand_totals['end_debit'] += t_totals['end_debit']
                grand_totals['end_credit'] += t_totals['end_credit']

            # Grand Total
            sheet.merge_range(y_offset, 0, y_offset, 6, 'TỔNG CỘNG BÁO CÁO', total_label_fmt)
            sheet.write(y_offset, 7,  grand_totals['qty'],        num_total_fmt)
            sheet.write(y_offset, 8,  '',                         empty_fmt)
            sheet.write(y_offset, 9,  grand_totals['debit'],      num_total_fmt)
            sheet.write(y_offset, 10, grand_totals['credit'],     num_total_fmt)
            sheet.write(y_offset, 11, grand_totals['end_debit'],  num_total_fmt)
            sheet.write(y_offset, 12, grand_totals['end_credit'], num_total_fmt)
            sheet.write(y_offset, 13, '',                         empty_fmt)
            sheet.write(y_offset, 14, '',                         empty_fmt)
            y_offset += 2

            # Ký tên
            now = datetime.now()
            date_str = f"Ngày {now.strftime('%d')} tháng {now.strftime('%m')} năm {now.strftime('%Y')}"
            sheet.merge_range(y_offset, 9, y_offset, total_cols, date_str,
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
            # Chia 15 cột cho 5 khối (0-2, 3-5, 6-8, 9-11, 12-14)
            blocks = [(0, 2), (3, 5), (6, 8), (9, 11), (12, 14)]
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
