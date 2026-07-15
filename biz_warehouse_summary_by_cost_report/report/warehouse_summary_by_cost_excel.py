# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import base64
import io
from datetime import datetime, date, time, timedelta

cols = {
    'code':0,
    'name':1,
    'code_pro':2,
    'name_pro':3,
    'code_ware':4,
    'name_ware':5,
    'dvt':6,
    'quantity_nhap':7,
    'value_nhap':8,
    'quantity_xuat':9,
    'value_xuat':10,
    'lenhsx':11,
}

class WarehouseSummaryByCostXlsx(models.AbstractModel):
    _name = 'report.biz_warehouse_summary_by_cost_report.w_s_b_c_xlxs'
    _description = 'w_s_b_c_xlxs'
    _inherit = 'report.report_xlsx.abstract'
    
    def generate_xlsx_report(self, workbook, data, details):
        for o in details:
            sheet = workbook.add_worksheet(u'BẢNG KÊ HÓA ĐƠN HHDV MUA VÀO')
            company_name_style = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 16,'align': 'center', 'valign':'vcenter', 'bold': True})
            
            info_stype = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'valign':'vcenter'})

            info_day_stype = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'valign':'vcenter','align': 'center', 'bold': True})

            title_table_style = workbook.add_format({'font_name': 'Times New Roman','bg_color': '#66CCFF', 'font_size': 12, 'valign':'vcenter','border': 1,'align': 'center','text_wrap': True})
            c_line_table_style = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'valign':'vcenter','align': 'center','text_wrap': True,'border': 1})
            r_line_table_style = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'valign':'vcenter','align': 'right','text_wrap': True,'border': 1})
            l_line_table_style = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'valign':'vcenter','align': 'left','text_wrap': True,'border': 1})
            sum_table_style = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'valign':'vcenter','align': 'left','text_wrap': True, 'bg_color': '#C0C0C0'})
            r_sum_table_style = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12, 'valign':'vcenter','align': 'right','text_wrap': True, 'bg_color': '#C0C0C0'})

            company = self.env.company

            sheet.set_column(0,0,20)
            sheet.set_column(1,1,20)
            sheet.set_column(2,2,20)
            sheet.set_column(3,3,25)
            sheet.set_column(4,4,20)
            sheet.set_column(5,5,25)
            sheet.set_column(6,6,20)
            sheet.set_column(7,7,25)
            sheet.set_column(8,8,25)
            sheet.set_column(9,9,25)
            sheet.set_column(10,10,25)
            sheet.set_column(11,11,25)


            sheet.set_row(0, 23)
            sheet.set_row(1, 20)
            sheet.set_row(2, 25)
            sheet.set_row(3, 25)

            y_offset = 0
            sheet.merge_range(y_offset, 0, y_offset, 11, 'TỔNG HỢP NHẬP, XUẤT KHO THEO ĐỐI TƯỢNG TẬP HỢP CHI PHÍ', company_name_style)
            y_offset += 1
            date = o.date_from
            sheet.merge_range(y_offset, 0, y_offset, 11, 'Tháng %s năm %s'%(date.strftime('%m'),date.strftime('%Y')), info_day_stype)
            y_offset += 1
            sheet.merge_range(y_offset, 0, y_offset+1, 0, 'Mã đối tượng THCP', title_table_style)
            sheet.merge_range(y_offset, 1, y_offset+1, 1, 'Tên đối tượng THCP', title_table_style)
            sheet.merge_range(y_offset, 2, y_offset+1, 2, 'Mã hàng', title_table_style)
            sheet.merge_range(y_offset, 3, y_offset+1, 3, 'Tên hàng', title_table_style)
            sheet.merge_range(y_offset, 4, y_offset+1, 4, 'Mã kho', title_table_style)
            sheet.merge_range(y_offset, 5, y_offset+1, 5, 'Tên kho', title_table_style)
            sheet.merge_range(y_offset, 6, y_offset+1, 6, 'ĐVT', title_table_style)
            sheet.merge_range(y_offset, 7, y_offset, 8, 'Nhập kho', title_table_style)
            sheet.merge_range(y_offset, 9, y_offset, 10, 'Xuất kho', title_table_style)
            sheet.write(y_offset+1, 7, 'Số lượng', title_table_style)
            sheet.write(y_offset+1, 8, 'Giá trị', title_table_style)
            sheet.write(y_offset+1, 9, 'Số lượng', title_table_style)
            sheet.write(y_offset+1, 10, 'Giá trị', title_table_style)
            sheet.merge_range(y_offset, 11, y_offset+1, 11, 'Lệnh sản xuất', title_table_style)
            y_offset += 2
            lines = self.get_lines(o)
            quantity_nhap = value_nhap = quantity_xuat = value_xuat = 0
            for line in lines:
                for key, val in line.items():
                    style = l_line_table_style
                    if key in ['quantity_nhap','value_nhap','quantity_xuat','value_xuat']:
                        style = r_line_table_style
                    if key == 'quantity_nhap':
                        quantity_nhap += val
                        val = "{:,.3f}".format(val).replace('.',',')
                    if key == 'value_nhap':
                        value_nhap += val
                        val = "{:,.0f}".format(val)
                    if key == 'quantity_xuat':
                        quantity_xuat += val
                        val = "{:,.3f}".format(val).replace('.',',')
                    if key == 'value_xuat':
                        value_xuat += val
                        val = "{:,.0f}".format(val)
                    sheet.write(y_offset, cols[key], val, style)
                y_offset += 1
            sheet.write(y_offset, 0, 'Số dòng = %s' %len(lines), sum_table_style)
            sheet.write(y_offset, 7, "{:,.3f}".format(quantity_nhap).replace('.',','), r_sum_table_style)
            sheet.write(y_offset, 8, "{:,.0f}".format(value_nhap), r_sum_table_style)
            sheet.write(y_offset, 9, "{:,.3f}".format(quantity_xuat).replace('.',','), r_sum_table_style)
            sheet.write(y_offset, 10, "{:,.0f}".format(value_xuat), r_sum_table_style)


    def get_lines(self,o):
        StockWarehouse = self.env['stock.warehouse'].sudo()
        Layers = self.env['stock.valuation.layer'].sudo()
        domain = self.domain_lay(o)
        result = []
        layers = Layers.search(domain + [('quantity','>',0),('stock_move_id.production_id','!=',False),('location_id.usage','in', ['supplier','production','inventory'])])
        productions = layers.mapped('stock_move_id.production_id')

        for layer in layers:
            result.append({
                'code': layer.product_id.default_code or '',
                'name': layer.product_id.name or '',
                'code_pro': layer.product_id.default_code or '',
                'name_pro': layer.product_id.name or '',
                'code_ware': layer.stock_move_id.location_dest_id.warehouse_id.code or '',
                'name_ware': layer.stock_move_id.location_dest_id.warehouse_id.name or '',
                'dvt': layer.product_id.uom_id and layer.product_id.uom_id.name or '',
                'quantity_nhap': abs(layer.quantity),
                'value_nhap': abs(layer.value),
                'quantity_xuat': 0,
                'value_xuat': 0,
                'lenhsx': layer.stock_move_id.production_id.name,
            })
            layers_relate = Layers.search(domain + [('stock_move_id.raw_material_production_id','=',layer.stock_move_id.production_id.id)])

            for layer_r in layers_relate:
                result.append({
                    'code': layer.product_id.default_code or '',
                    'name': layer.product_id.name or '',
                    'code_pro': layer_r.product_id.default_code or '',
                    'name_pro': layer_r.product_id.name or '',
                    'code_ware': layer_r.location_id.warehouse_id.code or '',
                    'name_ware': layer_r.location_id.warehouse_id.name or '',
                    'dvt': layer_r.product_id.uom_id and layer_r.product_id.uom_id.name or '',
                    'quantity_nhap': 0,
                    'value_nhap': 0,
                    'quantity_xuat': abs(layer_r.quantity),
                    'value_xuat': abs(layer_r.value),
                    'lenhsx': layer_r.stock_move_id.raw_material_production_id.name,
                })


        return result

    
    def domain_lay(self,o):
        date_from = datetime.combine(o.date_from, time.min) - timedelta(hours=7)
        date_to = datetime.combine(o.date_to, time.max) - timedelta(hours=7)
        return [
            ('product_id','!=',False),
            ('product_id.detailed_type','=','product'),
            ('create_date','>=', date_from),
            ('create_date','<=', date_to),
        ]



        










            
            