# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.modules.module import get_module_resource

import logging

_logger = logging.getLogger(__name__)

class stock_move_xlsx_report(models.AbstractModel):
    _name = "report.ccv_bao_cao.stock_move_xlsx_report"
    _inherit = "report.report_xlsx.abstract"
    _description = "Doanh số"  
    
    def get_data_export(self, data_src):
        p_date_from = data_src.get('start_date')
        p_date_to = data_src.get('end_date')
        team_id = data_src.get('team_id')

        def _get_move_domain(ref_list):
            domain = [
                ("reference", "ilike", ref_list[0]),
                ("state", "=", "done"),
                ("x_studio_sp_khuyn_mi", "=", False),
                ("x_studio_ngy_iu_chuyn", ">=", p_date_from),
                ("x_studio_ngy_iu_chuyn", "<=", p_date_to)
            ]
            if team_id:
                domain.insert(0, ("picking_id.sale_id.team_id.id", "=", team_id))
            return domain

        def _prepare_move_data(move, sign=1):
            sale_order = move.picking_id.sale_id
            if sale_order:
                order_line = move.sale_line_id
                order_line = order_line[0] if order_line else None
                unit_price = order_line.price_unit if order_line else 0
                total_price = unit_price * move.quantity_done * sign

                ngay_giao_hang = move.x_studio_ngy_iu_chuyn
                if ngay_giao_hang:
                    ngay_giao_hang = datetime.strftime(ngay_giao_hang, "%d/%m/%Y")

                return {
                    'ngay_giao_hang': ngay_giao_hang,
                    'bien_the_san_pham': move.product_id.display_name,
                    'partner_code': sale_order.sudo().partner_id.code_contact,
                    'don_hang': sale_order.sudo().name,
                    'nhan_vien_kinh_doanh': sale_order.user_id.name,
                    'doi_ngu_kinh_doanh': sale_order.sudo().team_id.report_name,
                    'thuc_the_khach_hang': sale_order.sudo().partner_id.name,
                    'sl_hoan_tat': move.quantity_done * sign,
                    'unit_price': unit_price,
                    'tong': total_price
                }

        data = []

        # Move Xuất
        out_domain = _get_move_domain(["/OUT"])
        moves_out = self.env['stock.move'].sudo().search(out_domain)

        for move in moves_out:
            move_data = _prepare_move_data(move, sign=1)
            if move_data:
                data.append(move_data)

        # Move Trả
        ret_domain = _get_move_domain(["KTP/RET", "KTP01/RET", "RET"])
        moves_ret = self.env['stock.move'].sudo().search(ret_domain)

        for move in moves_ret:
            move_data = _prepare_move_data(move, sign=-1)
            if move_data:
                data.append(move_data)

        return data


    def generate_xlsx_report(self, workbook, data, partners):
        # Create a worksheet
        worksheet = workbook.add_worksheet('Doanh số')

        data_raw = self.get_data_export(data)
        
        # Define your column headers
        headers = [
            'Ngày giao hàng',
            'Biến thể sản phẩm',
            'Đơn hàng',
            'Nhân viên kinh doanh',
            'Đội ngũ kinh doanh',
            'Mã khách hàng',
            'Khách hàng',
            'Số lượng giao',
            'Đơn giá',
            'Tổng'
        ]
        
        # Set the header row (row 0)
        bold = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, bold)

        # Add the data rows (starting from row 1)
        row = 1
        for record in data_raw:
            worksheet.write(row, 0, record['ngay_giao_hang'])
            worksheet.write(row, 1, record['bien_the_san_pham'])
            worksheet.write(row, 2, record['don_hang'])
            worksheet.write(row, 3, record['nhan_vien_kinh_doanh'])
            worksheet.write(row, 4, record['doi_ngu_kinh_doanh'])
            worksheet.write(row, 5, record['partner_code'])
            worksheet.write(row, 6, record['thuc_the_khach_hang'])
            worksheet.write(row, 7, record['sl_hoan_tat'])
            worksheet.write(row, 8, record['unit_price'])
            worksheet.write(row, 9, record['tong'])
            row += 1

        # Auto-adjust column widths
        for col_num in range(len(headers)):
            worksheet.set_column(col_num, col_num, 20)
