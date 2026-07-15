# -*- coding: utf-8 -*-
from odoo import models, _
import base64
import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class DetailsStockOrderBookXlsx(models.AbstractModel):
    _name = 'report.biz_details_purchase_report.stock_order_book_xlsx'
    _description = 'Báo cáo hàng tồn kho khu vực (Excel)'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, docs):
        self = self.with_context(lang=self.env.user.lang)
        for o in docs:
            company_id = self.env.company

            def get_format(*arguments):
                normal_style = {'font_name': 'Times New Roman', 'font_size': 11, 'valign': 'vcenter', 'align': 'left'}
                for arg in arguments:
                    normal_style.update(arg)
                return workbook.add_format(normal_style)

            report_title = {'bold': True, 'font_size': 16, 'align': 'center'}
            sub_title_format = {'font_size': 12, 'align': 'center', 'bold': True, 'italic': True}
            
            sheet = workbook.add_worksheet('Inventory Report')
            sheet.set_landscape()

            # Columns: STT, Mã hàng, Tên hàng, ĐVT, SL, Đơn hàng, Khách hàng, Khu vực, Nhà máy SX, Ngày SX, Ghi chú
            col_widths = [5, 12, 30, 8, 12, 18, 25, 15, 20, 12, 20]
            for i, w in enumerate(col_widths):
                sheet.set_column(i, i, w)

            total_cols = len(col_widths) - 1

            y_offset = 0
            # Logo & company
            image = company_id.logo or False
            slot_height = 60
            sheet.set_row(y_offset, slot_height)
            if image:
                image_data = io.BytesIO(base64.b64decode(image))
                sheet.insert_image(y_offset, 0, 'logo.png', {
                    'image_data': image_data, 'x_scale': 0.18, 'y_scale': 0.18,
                    'x_offset': 5, 'y_offset': 5
                })
            
            company_info = f"{company_id.name}\nMã số thuế: {company_id.vat or ''}\nĐịa chỉ: {company_id.street or ''} {company_id.street2 or ''}"
            sheet.merge_range(y_offset, 1, y_offset, total_cols, company_info, get_format({'align': 'left', 'font_size': 11, 'text_wrap': True}))
            y_offset += 1

            # Tiêu đề
            sheet.merge_range(y_offset, 0, y_offset, total_cols, 'BÁO CÁO HÀNG TỒN KHO KHU VỰC', get_format(report_title))
            y_offset += 1
            sheet.merge_range(y_offset, 0, y_offset, total_cols, f"Ngày {datetime.now().strftime('%d/%m/%Y')} - Kho: {', '.join(o.warehouse_ids.mapped('name'))}", get_format(sub_title_format))
            y_offset += 2

            # Header row
            headers = ['STT', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Số lượng', 'Đơn hàng', 'Khách hàng', 'Khu vực', 'Nhà máy SX', 'Ngày sản xuất', 'Ghi chú']
            for i, h in enumerate(headers):
                sheet.write(y_offset, i, h, get_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#E9ECEF'}))
            y_offset += 1

            # Body
            stt = 0
            total_qty = 0
            
            # Prepare formats
            num_fmt = get_format({'align': 'right', 'num_format': '#,##0.000', 'border': 1})
            txt_fmt = get_format({'align': 'left', 'border': 1, 'text_wrap': True})
            ctr_fmt = get_format({'align': 'center', 'border': 1})
            group_fmt = get_format({'bold': True, 'align': 'left', 'border': 1, 'bg_color': '#F8F9FA'})
            subtotal_fmt = get_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#FDFDFE'})
            num_subtotal_fmt = get_format({'bold': True, 'align': 'right', 'num_format': '#,##0.000', 'border': 1, 'bg_color': '#FDFDFE'})

            # Grouping logic
            from collections import defaultdict
            grouped_lines = defaultdict(list)
            for line in o.line_ids:
                grouped_lines[line.team_id].append(line)
            
            # Teams with names first, No Team (False) last
            sorted_teams = sorted(grouped_lines.keys(), key=lambda t: (not t, t.name or ''))

            for team in sorted_teams:
                team_name = (team.name if team else 'Hàng dự trữ (Không có Team)').upper()
                sheet.merge_range(y_offset, 0, y_offset, total_cols, f"KHU VỰC: {team_name}", group_fmt)
                y_offset += 1
                
                group_qty = 0
                lines = sorted(grouped_lines[team], key=lambda l: l.id)
                for line in lines:
                    stt += 1
                    group_qty += line.quantity
                    total_qty += line.quantity
                    
                    sheet.write(y_offset, 0,  stt, ctr_fmt)
                    sheet.write(y_offset, 1,  line.product_id.default_code or '', txt_fmt)
                    sheet.write(y_offset, 2,  line.product_id.name or '', txt_fmt)
                    sheet.write(y_offset, 3,  line.product_uom_id.name or '', ctr_fmt)
                    sheet.write(y_offset, 4,  line.quantity, num_fmt)
                    sheet.write(y_offset, 5,  line.order_id.name or 'Dự trữ', txt_fmt)
                    sheet.write(y_offset, 6,  line.partner_id.name or '', txt_fmt)
                    sheet.write(y_offset, 7,  line.team_name or '', txt_fmt)
                    sheet.write(y_offset, 8,  line.factory_name or '', txt_fmt)
                    sheet.write(y_offset, 9,  line.date_proc.strftime('%d/%m/%Y') if line.date_proc else '', ctr_fmt)
                    sheet.write(y_offset, 10, '', txt_fmt)
                    y_offset += 1
                
                # Subtotal row
                sheet.merge_range(y_offset, 0, y_offset, 3, f"TỔNG CỘNG KHU VỰC: {team_name}", subtotal_fmt)
                sheet.write(y_offset, 4, group_qty, num_subtotal_fmt)
                for i in range(5, 11):
                    sheet.write(y_offset, i, '', subtotal_fmt)
                y_offset += 1

            # Grand Total
            grand_total_fmt = get_format({'bold': True, 'align': 'center', 'border': 1, 'bg_color': '#DEE2E6'})
            num_grand_fmt = get_format({'bold': True, 'align': 'right', 'num_format': '#,##0.000', 'border': 1, 'bg_color': '#DEE2E6'})
            
            sheet.merge_range(y_offset, 0, y_offset, 3, "TỔNG CỘNG TẤT CẢ KHU VỰC", grand_total_fmt)
            sheet.write(y_offset, 4, total_qty, num_grand_fmt)
            for i in range(5, 11):
                sheet.write(y_offset, i, '', grand_total_fmt)
            y_offset += 2

            # Signatures
            now = datetime.now()
            date_str = f"Ngày {now.strftime('%d')} tháng {now.strftime('%m')} năm {now.strftime('%Y')}"
            sheet.merge_range(y_offset, total_cols - 2, y_offset, total_cols, date_str, get_format({'align': 'center', 'italic': True}))
            y_offset += 1

            roles = ['Người Lập', 'Trưởng khu vực', 'Phòng Kinh doanh', 'Phòng Kế toán', 'Thủ trưởng đơn vị']
            signers = [
                o.voter_id.name_without_position if o.voter_id else '',
                o.team_sale_id.name_without_position if o.team_sale_id else '',
                o.lead_sale_id.name_without_position if o.lead_sale_id else '',
                o.chief_finance_id.name_without_position if o.chief_finance_id else '',
                o.director_id.name_without_position if o.director_id else '',
            ]
            
            # Divide columns among 5 signatures (Total 11 columns)
            # 0-1, 2-3, 4-6, 7-8, 9-10
            blocks = [(0, 1), (2, 3), (4, 6), (7, 8), (9, 10)]
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, roles[i], get_format({'bold': True, 'align': 'center'}))
            
            y_offset += 5
            for i, (c_start, c_end) in enumerate(blocks):
                sheet.merge_range(y_offset, c_start, y_offset, c_end, signers[i], get_format({'bold': True, 'align': 'center'}))
