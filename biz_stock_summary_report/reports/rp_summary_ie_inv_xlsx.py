# -*- coding: utf-8 -*-
from odoo import api, models, fields
from datetime import datetime, timedelta, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class rp_summary_ie_inv_xlsx(models.AbstractModel):
    _name = 'report.biz_stock_summary_report.rp_summary_ie_inv_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "rp_summary_ie_inv_xlsx"
    
    def generate_xlsx_report(self, workbook, data, details):
        self = self.with_context(lang=self.env.user.lang)
        image_content = {'font_name': 'Times New Roman', 'font_size': 22, 'bold': True, 'align': 'center', 'valign':'vcenter'}
        table_border_head = {
            'font_name': 'Times New Roman', 'font_size': 12, 'text_wrap': True, 
            'align': 'center','border':True,'bold':True,
        }
        table_border_body = {'font_name': 'Times New Roman', 'border': True}

        def get_format(*arguments):
            normal_style = {'font_name': 'Times New Roman', 'font_size': 12,'valign':'vcenter','align': 'left'}
            for arg in arguments:
                normal_style.update(arg)
            return workbook.add_format(normal_style)

        for o in details:
            sheet = workbook.add_worksheet("Báo cáo tổng hợp nhập xuất tồn")
            sheet.set_column(0,0,15)
            sheet.set_column(1,1,15)
            sheet.set_column(2,2,15)
            sheet.set_column(3,3,15)
            sheet.set_column(4,11,15)

            view_tt = self.env.user.has_group('biz_stock_summary_report.group_ie_view_quant_and_tt')

            company = self.env.company
            y_offset=0
            sheet.merge_range(y_offset, 0, y_offset, 10,  company.name, 
                get_format({'bold': True}))
            y_offset+=1

            sheet.merge_range(y_offset, 0, y_offset, 10,  self.get_company_address(company), 
                get_format({'bold': True}))
            y_offset+=1

            sheet.merge_range(y_offset, 0, y_offset, 10,  company.phone, 
                get_format({'bold': True}))
            y_offset+=1

            y_offset+=1
            sheet.merge_range(y_offset, 0, y_offset, 10,  'BẢNG TỔNG HỢP NHẬP - XUẤT - TỒN KHO HÀNG HÓA', 
                get_format({'font_size': 16,'align': 'center', 'bold': True}))
            y_offset+=1
            
            sheet.merge_range(y_offset, 0, y_offset, 10, "Tháng %s Năm %s" % (o.from_date.strftime('%m'), o.from_date.strftime('%Y')), 
                get_format({'align': 'center', 'text_wrap': True, 'italic': True}))
            y_offset+=2

            sheet.merge_range(y_offset, 0, y_offset +1, 0, 'Mã Hàng', get_format(table_border_head))
            sheet.merge_range(y_offset, 1, y_offset +1, 1, 'Tên Hàng', get_format(table_border_head))
            sheet.merge_range(y_offset, 2, y_offset +1, 2, 'ĐVT', get_format(table_border_head))
            sheet.merge_range(y_offset, 3, y_offset, 4, 'Đầu kỳ', get_format(table_border_head))
            sheet.merge_range(y_offset, 5, y_offset,6, 'Nhập kho', get_format(table_border_head))
            sheet.merge_range(y_offset, 7, y_offset, 8, 'Xuất kho', get_format(table_border_head))
            sheet.merge_range(y_offset, 9, y_offset, 10, 'Cuối kỳ', get_format(table_border_head))
            # sheet.write(y_offset +1, 7, 'Đơn giá xuất kho', get_format(table_border_head))
            if view_tt:
                sheet.write(y_offset +1, 3, 'Số lượng', get_format(table_border_head))
                sheet.write(y_offset +1, 4, 'Giá trị', get_format(table_border_head))
                sheet.write(y_offset +1, 5, 'Số lượng', get_format(table_border_head))
                sheet.write(y_offset +1, 6, 'Giá trị', get_format(table_border_head))
                sheet.write(y_offset +1, 7, 'Số lượng', get_format(table_border_head))
                sheet.write(y_offset +1, 8, 'Giá trị', get_format(table_border_head))
                sheet.write(y_offset +1, 9, 'Số lượng', get_format(table_border_head))
                sheet.write(y_offset +1, 10, 'Giá trị', get_format(table_border_head))
            else:
                sheet.merge_range(y_offset +1, 3, y_offset +1, 4, 'Số lượng', get_format(table_border_head))
                sheet.merge_range(y_offset +1, 5, y_offset +1, 6, 'Số lượng', get_format(table_border_head))
                sheet.merge_range(y_offset +1, 7, y_offset +1, 8, 'Số lượng', get_format(table_border_head))
                sheet.merge_range(y_offset +1, 9, y_offset +1, 10, 'Số lượng', get_format(table_border_head))
            
            y_offset+=2

            qty_begin = value_begin = 0
            qty_import = value_import = 0
            qty_export = value_export = 0
            qty_end = value_end = 0

            for line in o.line_ids:
                qty_begin += line.qty_begin
                value_begin += line.value_begin
                qty_import += line.qty_import
                value_import += line.value_import
                qty_export += line.qty_export
                value_export += line.value_export
                qty_end += line.qty_end
                value_end += line.value_end

                sheet.write(y_offset, 0, line.product_code or '', get_format(table_border_body))
                sheet.write(y_offset, 1, line.product_id.name or '', get_format(table_border_body))
                sheet.write(y_offset, 2, line.uom_id.name or '', get_format(table_border_body, {'align': 'center'}))
                if view_tt:
                    sheet.write(y_offset, 3, line.qty_begin , get_format(table_border_body, {'align': 'center'}))
                    sheet.write(y_offset, 4, line.value_begin, get_format(table_border_body, {'align': 'center'}))
                    sheet.write(y_offset, 5, line.qty_import , get_format(table_border_body, {'align': 'center'}))
                    sheet.write(y_offset, 6, line.value_import, get_format(table_border_body, {'align': 'center'}))
                    sheet.write(y_offset, 7, line.qty_export, get_format(table_border_body, {'align': 'center'}))
                    sheet.write(y_offset, 8, line.value_export, get_format(table_border_body, {'align': 'right'}))
                    sheet.write(y_offset, 9, line.qty_end, get_format(table_border_body, {'align': 'center'}))
                    sheet.write(y_offset, 10, line.value_end, get_format(table_border_body, {'align': 'center'}))

                else:
                    sheet.merge_range(y_offset, 3, y_offset, 4, line.qty_begin , get_format(table_border_body, {'align': 'center'}))
                    sheet.merge_range(y_offset, 5, y_offset, 6,line.qty_import , get_format(table_border_body, {'align': 'center'}))
                    sheet.merge_range(y_offset, 7, y_offset, 8, line.qty_export, get_format(table_border_body, {'align': 'center'}))
                    sheet.merge_range(y_offset, 9, y_offset, 10, line.qty_end, get_format(table_border_body, {'align': 'center'}))

                y_offset+=1

            # Tổng
            sheet.write(y_offset, 0, '', get_format(table_border_body, {'align': 'center'}))
            sheet.write(y_offset, 1, 'Tổng cộng', get_format(table_border_body, {'align': 'center', 'bold': True}))
            sheet.write(y_offset, 2, '', get_format(table_border_body, {'align': 'center', 'bold': True}))
            if view_tt:
                sheet.write(y_offset, 3, qty_begin , get_format(table_border_body, {'align': 'center', 'bold': True}))
                sheet.write(y_offset, 4, value_begin, get_format(table_border_body, {'align': 'center', 'bold': True}))
                sheet.write(y_offset, 5, qty_import , get_format(table_border_body, {'align': 'center', 'bold': True}))
                sheet.write(y_offset, 6, value_import, get_format(table_border_body, {'align': 'center', 'bold': True}))
                sheet.write(y_offset, 7, qty_export, get_format(table_border_body, {'align': 'center', 'bold': True}))
                sheet.write(y_offset, 8, value_export, get_format(table_border_body, {'align': 'right'}))
                sheet.write(y_offset, 9, qty_end, get_format(table_border_body, {'align': 'center', 'bold': True}))
                sheet.write(y_offset, 10, value_end, get_format(table_border_body, {'align': 'center', 'bold': True}))
            else:
                sheet.merge_range(y_offset, 3, y_offset, 4, qty_begin , get_format(table_border_body, {'align': 'center', 'bold': True}))
                sheet.merge_range(y_offset, 5, y_offset, 6, qty_import , get_format(table_border_body, {'align': 'center', 'bold': True}))
                sheet.merge_range(y_offset, 7, y_offset, 8, qty_export, get_format(table_border_body, {'align': 'center', 'bold': True}))
                sheet.merge_range(y_offset, 9, y_offset, 10, qty_end, get_format(table_border_body, {'align': 'center', 'bold': True}))

            y_offset+=2
            # sheet.merge_range(y_offset, 9, y_offset, 11, 'Hà nội, %s' % datetime.now().strftime('Ngày %d tháng %m năm %Y'), get_format({'italic': True, 'align': 'center'}))
            # y_offset+=1

            sheet.write(y_offset, 1, 'Người lập biếu', get_format({'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 3, y_offset, 5, 'Kế toán trưởng', get_format({'bold': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 8, y_offset, 10, 'Người phê duyệt', get_format({'bold': True, 'align': 'center'}))
            y_offset+=1

            sheet.write(y_offset, 1, '(Ký, họ tên)', get_format({'italic': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 3, y_offset, 5, '(Ký, họ tên)', get_format({'italic': True, 'align': 'center'}))
            sheet.merge_range(y_offset, 8, y_offset, 10, '(Ký, họ tên, đóng dấu)', get_format({'italic': True, 'align': 'center'}))


    def get_company_address(self, company):
        address = ''
        if company:
            if company.street:
                address += company.street
            if company.street2:
                address += len(address) > 0 and ', ' + company.street2 or company.street2
            if company.city:
                address += len(address) > 0 and ', ' + company.city or company.city
            if company.state_id:
                address += len(address) > 0 and ', ' + company.state_id.name or company.state_id.name
            if company.country_id:
                address += len(address) > 0 and ', ' + company.country_id.name or company.country_id.name
        return address