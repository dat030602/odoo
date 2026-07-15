# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import base64
import io
from urllib.request import Request, urlopen

cols = {
    'stt':0,
    'ma_so':1,
    'ngay':2,
    'nguoimua':3,
    'msthue':4,
    'danhthu':5,
    'thue':6,
    'ghichu':7,
}

type_vat_name = {
    'no_vat': '1. Hàng hóa, dịch vụ không chịu thuế giá trị gia tăng (GTGT):',
    '0_vat': '2. Hàng hóa, dịch vụ chịu thuế suất thuế GTGT 0%:',
    '5_vat': '3. Hàng hóa, dịch vụ chịu thuế suất thuế GTGT 5%:',
    '8_vat': '3. Hàng hóa, dịch vụ chịu thuế suất thuế GTGT 8%:',
    '10_vat': '4. Hàng hóa, dịch vụ chịu thuế suất thuế GTGT 10%:',
    'no_tax': '5. Hàng hóa, dịch vụ bán ra không tính thuế:'
}


class report_invoice_list_xlsx(models.AbstractModel):
    _name = 'report.biz_sales_invoice_list.report_invoice_list_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'report_invoice_list_xlsx'
    
    def generate_xlsx_report(self, workbook, data, o):
        self = self.with_context(lang=self.env.user.lang)
        table_border_head = {
            'font_name': 'Times New Roman', 'font_size': 12, 'text_wrap': True, 
            'align': 'center','border':True,'bold':True, 'bg_color': '#f7ad00'
        }
        table_border_body = {'font_name': 'Times New Roman', 'font_size': 12, 'align': 'left','border':True,'num_format': '#,###'}
        not_border_body = {'font_name': 'Times New Roman', 'font_size': 12, 'align': 'center','valign':'vcenter','num_format': '#,###'}


        def get_format(*arguments):
            normal_style = {'font_name': 'Times New Roman', 'font_size': 12,'valign':'vcenter','align': 'left'}
            for arg in arguments:
                normal_style.update(arg)
            return workbook.add_format(normal_style)

        sheet = workbook.add_worksheet("BẢNG KÊ HÓA ĐƠN HHDV BÁN RA")
        sheet.set_margins(0.25,0.25,0.25,0.75)
        sheet.set_column(0,7,15)
        y_offset = 0
        sheet.merge_range(y_offset, 0, y_offset, 7, 'BẢNG KÊ HÓA ĐƠN, CHỨNG TỪ HÀNG HÓA, DỊCH VỤ BÁN RA', 
            get_format({'align': 'center','font_size': 16, 'bold': True,'bottom': 1, 'top': 1, 'bg_color': '#f7f700'}))

        y_offset +=1

        from_date_str = o.from_date.strftime('%d/%m/%Y')
        to_date_str = o.to_date.strftime('%d/%m/%Y')

        sheet.merge_range(y_offset,  0, y_offset, 7, 'Kỳ tính thuế: %s - %s' % (from_date_str, to_date_str), 
            get_format({'align': 'center', 'bold': True}))

        y_offset +=1

        # Table header

        sheet.merge_range(y_offset, 0 , y_offset +1, 0, 'STT', get_format(table_border_head))
        sheet.merge_range(y_offset, 1 , y_offset, 2, 'Hóa đơn, chứng từ', get_format(table_border_head))
        sheet.write(y_offset +1, 1, 'Số hóa đơn', get_format(table_border_head))
        sheet.write(y_offset +1, 2, 'Ngày, tháng, năm lập hóa đơn', get_format(table_border_head))
        sheet.merge_range(y_offset, 3 , y_offset +1, 3, 'Tên người mua', get_format(table_border_head))
        sheet.merge_range(y_offset, 4 , y_offset +1, 4, 'Mã số thuế', get_format(table_border_head))
        sheet.merge_range(y_offset, 5 , y_offset +1, 5, 'Doanh thu chưa có thuế GTGT', get_format(table_border_head))
        sheet.merge_range(y_offset, 6 , y_offset +1, 6, 'Thuế GTGT', get_format(table_border_head))
        sheet.merge_range(y_offset, 7 , y_offset +1, 7, 'Ghi chú', get_format(table_border_head))
        y_offset+=2
        i = 0
        for so in ['[1]','[2]','[3]','[4]','[5]','[6]','[7]','[8]']:
            sheet.write(y_offset, i, so, get_format(table_border_body,{'align': 'center'}))
            i += 1
        y_offset +=1
        
        # Table body

        for type_vat in ['no_vat','0_vat','5_vat','8_vat','10_vat','no_tax']: 
            lines = self.get_lines(o, type_vat)

            sheet.merge_range(y_offset, 0, y_offset,  3, type_vat_name[type_vat], get_format(table_border_body,{'bold': True}))

            sheet.write(y_offset, 4, '', get_format(table_border_body))
            sheet.write(y_offset, 5, '', get_format(table_border_body,{'align': 'right'}))
            sheet.write(y_offset, 6, '', get_format(table_border_body,{'align': 'right'}))
            sheet.write(y_offset, 7, '', get_format(table_border_body))
            y_offset +=1
            stt = 0
            for line in lines:
                line_type = line.pop('type')
                if line_type == 'line':
                    stt +=1
                    for key, val in line.items():
                        if key == 'stt':
                            val = stt
                        table_border_body_custom = get_format(table_border_body)
                        if cols[key] in [5,6]:
                            table_border_body_custom = get_format(table_border_body,{'align': 'right'})

                        sheet.write(y_offset, cols[key], val, table_border_body_custom)

                    y_offset +=1
                if line_type == 'total':
                    for key, val in line.items():
                        table_border_body_total = get_format(table_border_body)
                        if cols[key] in [5,6]:
                            table_border_body_total = get_format(table_border_body,{'bold': True, 'align': 'right','bg_color': '#F6DB36'})
                        sheet.write(y_offset, cols[key], val, table_border_body_total)
                    y_offset +=1
                if line_type == 'total_title':
                    for key, val in line.items():
                        sheet.write(y_offset, cols[key], val, get_format(not_border_body))
                    y_offset +=2

        sheet.merge_range(y_offset, 1, y_offset,  6, 'Kê khai các hóa đơn đầu ra đã xuất bán HH-DV trong kỳ', get_format(table_border_body,{'bold': True,'bg_color':'yellow','valign':'center','align':'center'}))
        y_offset += 1
        sheet.merge_range(y_offset, 1, y_offset,  6, 'Không kê khai các hóa đơn của các kỳ khác', get_format(table_border_body,{'bold': True,'bg_color':'yellow','valign':'center','align':'center'}))
        y_offset += 1
        sheet.merge_range(y_offset, 1, y_offset,  6, 'Không kê khai các hóa đơn xóa bỏ (HĐ viết sai)', get_format(table_border_body,{'bold': True,'bg_color':'yellow','valign':'center','align':'center'}))
        y_offset += 1

    def get_lines(self, o, type=False):
        remove_customer_reports = self.env.company.remove_customer_reports
        domain = [
            ('move_id.state','=', 'posted'),
            ('move_id.date','>=', o.from_date),
            ('move_id.date','<=', o.to_date),
            ('move_id.company_id','=',self.env.company.id),
            ('move_id.journal_id.type','=','sale')
        ]
        if remove_customer_reports == True:
            domain.append(('move_id.move_type', '!=', 'out_refund'))
        name_vat = False
        if type == 'no_vat':
            domain += ['|','&',('product_id.product_not_taxable','=', True),('tax_ids','=', False),'&',('product_not_taxable','=', True),('tax_ids','=', False)]            

        if type == '0_vat':
            name_vat = 'Thuế GTGT phải nộp 0%'
            domain += [('tax_ids.type_tax_use','=', 'sale'),('tax_ids.type_vat','=', type)]

        if type == '5_vat':
            name_vat = 'Thuế GTGT phải nộp 5%'
            domain += [('tax_ids.type_tax_use','=', 'sale'),('tax_ids.type_vat','=', type)]

        if type == '8_vat':
            name_vat = 'Thuế GTGT phải nộp 8%'
            domain += [('tax_ids.type_tax_use','=', 'sale'),('tax_ids.type_vat','=', type)]

        if type == '10_vat':
            name_vat = 'Thuế GTGT phải nộp 10%'
            domain += [('tax_ids.type_tax_use','=', 'sale'),('tax_ids.type_vat','=', type)]

        if type == 'no_tax':
            domain += [('product_id.product_not_taxable','=', False),('tax_ids','=', False)]

        movelines = self.env['account.move.line'].search(domain,order="date asc")
        move_ids = movelines.mapped('move_id')

        result = []
        sum_dt = 0
        sum_thue = 0
        tax_search_ids = self.env['account.tax'].search([('type_tax_use','=', 'sale'),('name','=', name_vat)]) if name_vat else False
        tag_ids = tax_search_ids.invoice_repartition_line_ids.mapped('tag_ids').ids if tax_search_ids else False
        for move in sorted(move_ids,key=lambda x:(x.date,x.name)):
            move_doanhthu = move.line_ids.filtered(lambda x: x.account_id and x.account_id.account_type == 'income' and self.check_tax(x.tax_ids,name_vat) == True)\
            if name_vat else move.line_ids.filtered(lambda x: x.id in movelines.ids)
            doanhthu = sum(move_doanhthu.mapped('credit')) - sum(move_doanhthu.mapped('debit'))

            move_thue = move.line_ids.filtered(lambda x: x.account_id and x.account_id.is_output_vat)
            if name_vat:
                move_thue = move_thue.filtered(lambda x: list(filter(lambda y: y in tag_ids,x.tax_tag_ids.ids)))
            
            thue = 0 if type in ['no_vat','no_tax'] else sum(move_thue.mapped('credit')) - sum(move_thue.mapped('debit'))

            sum_dt += doanhthu
            sum_thue += thue

            vals = {
                'stt':0,
                'ma_so':move.name,
                'ngay': move.date and move.date.strftime('%d/%m/%Y') or '',
                'nguoimua': move.partner_id.name or '',
                'msthue': move.partner_id.vat or '',
                'danhthu':doanhthu,
                'thue':thue,
                'ghichu': '',
                'type': 'line'
            }
            result.append(vals)

        val_thue = ''
        if type in ['5_vat','8_vat','10_vat']:
            val_thue = sum_thue

        result.append({
            'stt': '',
            'ma_so': '',
            'ngay': '',
            'nguoimua': '',
            'msthue': '',
            'danhthu': sum_dt,
            'thue': val_thue,
            'ghichu': '',
            'type': 'total'
        })
        if type == 'no_vat':
            result.append({
                'stt': '',
                'ma_so': '',
                'ngay': '',
                'nguoimua': '',
                'msthue': '',
                'danhthu': 'Tổng[26]',
                'thue': '',
                'ghichu': '',
                'type': 'total_title'
            })            

        if type == '0_vat':
            result.append({
                'stt': '',
                'ma_so': '',
                'ngay': '',
                'nguoimua': '',
                'msthue': '',
                'danhthu': 'Tổng[29]',
                'thue': '',
                'ghichu': '',
                'type': 'total_title'
            })  

        if type == '5_vat':
            result.append({
                'stt': '',
                'ma_so': '',
                'ngay': '',
                'nguoimua': '',
                'msthue': '',
                'danhthu': 'Tổng [30]',
                'thue': 'Tổng [31]',
                'ghichu': '',
                'type': 'total_title'
            })  

        if type == '10_vat':
            result.append({
                'stt': '',
                'ma_so': '',
                'ngay': '',
                'nguoimua': '',
                'msthue': '',
                'danhthu': 'Tổng [32]',
                'thue': 'Tổng [33]',
                'ghichu': '',
                'type': 'total_title'
            })  

        if type == 'no_tax':
            result.append({
                'stt': '',
                'ma_so': '',
                'ngay': '',
                'nguoimua': '',
                'msthue': '',
                'danhthu': 'Tổng [32a]',
                'thue': '',
                'ghichu': '',
                'type': 'total_title'
            })  

        return result

    def check_tax(self,tax_ids,name_vat):
        if name_vat:
            if tax_ids.filtered(lambda x: x.name == name_vat):
                return True
            return False

        return True

