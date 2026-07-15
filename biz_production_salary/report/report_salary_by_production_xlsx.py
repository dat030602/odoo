# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import base64
import io
from urllib.request import Request, urlopen

cols = {
    'ten_hang':0,
    'cong_nhat':1,
    'san_luong':2,
    'nhap_hang':3,
    'xuat_hang':4,
    'san_xuat':5,
    'tong_sl':6,
    'don_gia':7,
    'thanh_tien':8
}

class report_salary_by_production_xlsx(models.AbstractModel):
    _name = 'report.biz_production_salary.report_salary_by_production_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'report_salary_by_production_xlsx'
    
    def generate_xlsx_report(self, workbook, data, o):
        self = self.with_context(lang=self.env.user.lang)
        table_border_head = {
            'font_name': 'Times New Roman', 'font_size': 12, 'text_wrap': True, 
            'align': 'center','border':True,'bold':True
        }
        table_border_body = {'font_name': 'Times New Roman', 'font_size': 12, 'align': 'left','border':True}


        def get_format(*arguments):
            normal_style = {'font_name': 'Times New Roman', 'font_size': 12,'valign':'vcenter','align': 'left'}
            for arg in arguments:
                normal_style.update(arg)
            return workbook.add_format(normal_style)

        sheet = workbook.add_worksheet("BÁO CÁO LƯƠNG THEO SẢN LƯỢNG")
        sheet.set_margins(0.25,0.25,0.25,0.75)
        sheet.set_column(0,0,45)
        sheet.set_column(1,1,20)
        sheet.set_column(2,2,20)
        sheet.set_column(3,3,20)
        sheet.set_column(4,4,20)
        sheet.set_column(5,5,20)
        sheet.set_column(6,6,20)
        sheet.set_column(7,7,30)
        sheet.set_column(8,8,30)
        
        y_offset = 0
        sheet.merge_range(y_offset, 0, y_offset, 8, 'BÁO CÁO LƯƠNG THEO SẢN LƯỢNG XUẤT - NHẬP %s'%(o.department_id and o.department_id.name.upper() or ''), 
            get_format({'align': 'center','font_size': 18, 'bold': True}))
        sheet.set_row(y_offset, 25)
        y_offset += 1
        sheet.merge_range(y_offset, 0, y_offset, 8, 'TỪ %s -> %s'%((o.date_from and o.date_from.strftime('NGÀY %d THÁNG %m NĂM %Y') or ''),(o.date_to and o.date_to.strftime('NGÀY %d THÁNG %m NĂM %Y') or '')), 
            get_format({'align': 'center','font_size': 16}))
        sheet.set_row(y_offset, 25)
        y_offset += 1
        # Table header
        sheet.merge_range(y_offset, 0 , y_offset +1, 0, 'TÊN HÀNG', get_format(table_border_head))
        sheet.merge_range(y_offset, 1 , y_offset, 6, 'SỐ LƯỢNG', get_format(table_border_head))
        sheet.write(y_offset+1, 1, 'CÔNG NHẬT', get_format(table_border_head))
        sheet.write(y_offset+1, 2, 'SẢN LƯỢNG KHÁC', get_format(table_border_head))
        sheet.write(y_offset+1, 3, 'NHẬP HÀNG', get_format(table_border_head))
        sheet.write(y_offset+1, 4, 'XUẤT HÀNG', get_format(table_border_head))
        sheet.write(y_offset+1, 5, 'SẢN XUẤT', get_format(table_border_head))
        sheet.write(y_offset+1, 6, 'TỔNG SL', get_format(table_border_head))
        sheet.merge_range(y_offset, 7,  y_offset +1, 7, 'ĐƠN GIÁ', get_format(table_border_head))
        sheet.merge_range(y_offset, 8 , y_offset +1, 8, 'THÀNH TIỀN', get_format(table_border_head))
        y_offset += 2
        lines = self.get_lines(o)
        for key in sorted(lines.keys(), key=lambda d: datetime.strptime(d, '%d/%m/%Y')):
            val = lines[key]
            sheet.merge_range(y_offset, 0, y_offset, 8, key, get_format(table_border_body, {'bold': True}))
            y_offset += 1
            for vl in val:
                add_style = {}
                if vl.get('ten_hang') == 'TỔNG CỘNG':
                    add_style.update({'bold': True})
                for k, v in vl.items():
                    if k in ['cong_nhat', 'san_luong', 'nhap_hang', 'xuat_hang', 'tong_sl', 'don_gia', 'thanh_tien', 'san_xuat']:
                        add_style.update({'align': 'right'})
                        number_format = get_format(table_border_body, add_style, {'num_format': '#,##0'})

                        try:
                            v = float(v)
                        except (ValueError, TypeError):
                            v = 0.0
                        sheet.write_number(y_offset, cols[k], v, number_format)
                    else:
                        sheet.write(y_offset, cols[k], v, get_format(table_border_body, add_style))

                y_offset += 1

    def get_lines(self,o):
        merge = {}
        for line in o.line_ids:
            merge_name = line.date.strftime('%d/%m/%Y') if line.date else False
            data = {
                'ten_hang': line.product_id.name if line.product_id else '',
                'cong_nhat': line.day_labor,
                'san_luong': line.other_output,
                'nhap_hang': line.input_pro,
                'xuat_hang': line.output_pro,
                'san_xuat': line.production,
                'tong_sl': line.total_quantity,
                'don_gia': line.price_unit,
                'thanh_tien': line.total_amount
            }
            if merge_name not in merge:
                merge.setdefault(merge_name,[data])
            else:
                merge[merge_name].append(data)
        for key,val in merge.items():
            data = {
                'ten_hang': 'TỔNG CỘNG',
                'cong_nhat': 0,
                'san_luong': 0,
                'nhap_hang': 0,
                'xuat_hang': 0,
                'san_xuat': 0,
                'tong_sl': 0,
                'don_gia': '',
                'thanh_tien': 0
            }
            for vl in val:
                for k in data.keys():
                    if k not in ['ten_hang','don_gia']:
                        data[k] += vl.get(k)
            merge[key].append(data)
        return merge
