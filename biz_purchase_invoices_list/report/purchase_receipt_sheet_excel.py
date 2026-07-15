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
    'nguoiban':3,
    'msthue':4,
    'giatri_hhdv_muavao':5,
    'tongsothue_gtgt_dauvao':6,
    'sothue_gtgt_dudk_khautru':7,
    'ghichu':8,
}

class PurchaseReceipSheetXlsx(models.AbstractModel):
    _name = 'report.biz_purchase_invoices_list.purchase_receipt_sheet_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "purchase_receipt_sheet_xlsx"
    
    def generate_xlsx_report(self, workbook, data, details):
        for o in details:
            sheet = workbook.add_worksheet(u'BẢNG KÊ HÓA ĐƠN HHDV MUA VÀO')
            company_name_style = workbook.add_format({'font_name': 'Times New Roman', 'font_size': 20,'align': 'center', 'valign':'vcenter', 'bold': True,'font_color': 'red'})
            company_name_style.set_bg_color('yellow')
            company_name_style.set_border()
            title_style = workbook.add_format({'font_name': 'Times New Roman', 'align': 'center', 'valign':'vcenter', 'font_size': 16,'bold': True,'font_color': 'blue'})
            title_style.set_border()
            title_table_style = workbook.add_format({'font_name': 'Times New Roman', 'align': 'center', 'valign':'vcenter', 'font_size': 13,'bold': True,'text_wrap': True})
            title_table_style.set_border()
            title_table_style.set_bg_color('#CCFFCC')
            line_table = workbook.add_format({'font_name': 'Times New Roman', 'align': 'center', 'valign':'vcenter', 'font_size': 13,'text_wrap': True,'num_format': '#,###'})
            line_table.set_border()
            
            line_table_right = workbook.add_format({'font_name': 'Times New Roman', 'align': 'right', 'valign':'vcenter', 'font_size': 13,'text_wrap': True,'num_format': '#,###'})
            line_table_right.set_border()

            total_line_table = workbook.add_format({'font_name': 'Times New Roman', 'align': 'center', 'valign':'vcenter', 'font_size': 13,'text_wrap': True,'bold': True,'num_format': '#,###'})
            total_line_table.set_border()
            total_line_table.set_bg_color('yellow')

            
            total_line_table_left_red = workbook.add_format({'font_name': 'Times New Roman','bg_color': 'yellow','font_color':'red', 'align': 'right','num_format': '#,###', 'valign':'vcenter', 'font_size': 13,'text_wrap': True,'bold': True})
            total_line_table_left_red.set_border()

            total_line_table_left = workbook.add_format({'font_name': 'Times New Roman', 'align': 'right', 'valign':'vcenter', 'font_size': 13,'text_wrap': True,'num_format': '#,###','bold': True})
            total_line_table_left.set_border()
            total_line_table_left.set_bg_color('yellow')

            special_line_style = workbook.add_format({'font_name': 'Times New Roman', 'valign':'vcenter', 'font_size': 13,'bold': True,'text_wrap': True,'num_format': '#,###'})
            red = workbook.add_format({"color": "red",'bold':True})

            def get_rich_string(offset,text):
                return sheet.write_rich_string(
                    offset,0,  text[0],red, text[1], special_line_style, text[2], special_line_style
                )

            sheet.set_margins(0.25,0.25,0.25,0.75)
            sheet.set_column(0,0,10)
            sheet.set_column(1,1,15)
            sheet.set_column(2,2,18)
            sheet.set_column(3,3,45)
            sheet.set_column(4,4,25)
            sheet.set_column(5,5,23)
            sheet.set_column(6,6,23)
            sheet.set_column(7,7,25)
            sheet.set_column(8,8,23)
            sheet.set_row(0, 30)
            sheet.set_row(1, 30)
            sheet.set_row(2, 45)
            sheet.set_row(3, 40)

            y_offset = 0
            sheet.merge_range(y_offset, 0, y_offset, 8, 'BẢNG KÊ HÓA ĐƠN, CHỨNG TỪ HÀNG HÓA, DỊCH VỤ MUA VÀO', company_name_style)
            y_offset += 1
            sheet.merge_range(y_offset, 0, y_offset, 8, 'Kỳ tính thuế: Từ ngày %s đến ngày %s'%((o.date_from and o.date_from.strftime('%d/%m/%Y') or ''),\
                (o.date_to and o.date_to.strftime('%d/%m/%Y') or '')), title_style)
            y_offset += 1
            sheet.merge_range(y_offset, 0, y_offset+1, 0, 'STT', title_table_style)
            sheet.merge_range(y_offset, 1, y_offset, 2, 'Hóa đơn, chứng từ, biên lai nộp thuế', title_table_style)
            sheet.write(y_offset +1, 1, 'Số hóa đơn', title_table_style)
            sheet.write(y_offset +1, 2, 'Ngày, tháng, năm lập hóa đơn', title_table_style)
            sheet.merge_range(y_offset, 3 , y_offset +1, 3, 'Tên người bán', title_table_style)
            sheet.merge_range(y_offset, 4 , y_offset +1, 4, 'Mã số thuế người bán', title_table_style)
            sheet.merge_range(y_offset, 5 , y_offset +1, 5, 'Giá trị HH-DV mua vào', title_table_style)
            sheet.merge_range(y_offset, 6 , y_offset +1, 6, 'Tổng số Thuế GTGT đầu vào', title_table_style)
            sheet.merge_range(y_offset, 7 , y_offset +1, 7, 'Số thuế GTGT đủ ĐK khấu trừ', title_table_style)
            sheet.merge_range(y_offset, 8 , y_offset +1, 8, 'Ghi chú', title_table_style)
            total_23 = 0
            total_24 = 0
            total_25 = 0

            y_offset += 2
            i = 0
            for so in ['[1]','[2]','[3]','[4]','[5]','[6]','[7]','[8]','[9]']:
                sheet.write(y_offset, i, so, title_table_style)
                i += 1
            y_offset += 1
            for type in ['private_use', 'shared_use']:
                lines = self.get_lines(o,type)
                sheet.merge_range(y_offset, 0 , y_offset, 8, '', special_line_style)
                text = False
                if type == 'private_use':
                    text = ('Hàng hóa, dịch vụ dùng',' riêng ','cho SXKD chịu thuế GTGT')
                if type == 'shared_use':
                    text = ('Hàng hóa, dịch vụ dùng',' chung ','cho SXKD chịu thuế GTGT và không chịu thuế đủ điều kiện khấu trừ thuế')
                get_rich_string(y_offset,text)
                y_offset +=1
                stt = 0
                for line in lines:
                    line_type = line.pop('type')
                    if line_type == 'line':
                        stt +=1
                        for key, val in line.items():
                            if key == 'stt':
                                val = stt
                            style = line_table
                            if cols[key] in [5,6,7]:
                                style = line_table_right
                            sheet.write(y_offset, cols[key], val, style)

                        y_offset +=1
                    else:
                        for key, val in line.items():
                            style = total_line_table if cols[key] in [3,4,5,6,7]\
                             else line_table

                            if cols[key] in [5,6,7]:
                                style = total_line_table_left

                            if cols[key] == 5:
                                total_23 += int(float(val.replace(",",""))) if isinstance(val, str) else val
                            if cols[key] == 6:
                                total_24 += int(float(val.replace(",",""))) if isinstance(val, str) else val
                            if cols[key] == 7:
                                total_25 += int(float(val.replace(",",""))) if isinstance(val, str) else val
                            sheet.write(y_offset, cols[key], val, style)

                        y_offset +=2

            sheet.merge_range(y_offset, 0 , y_offset, 3, 'Tổng giá trị HHDV mua vào phục vụ SXKD được khấu trự thuế GTGT:', special_line_style)
            sheet.write(y_offset, 4, '', total_line_table)
            sheet.write(y_offset, 5, 'Chỉ tiêu[23]', total_line_table)
            sheet.write(y_offset, 6, total_23 and "{:,.0f}".format(total_23) or 0, total_line_table_left_red)
            y_offset += 1

            sheet.merge_range(y_offset, 0 , y_offset, 3, 'Tổng số thuế GTGT của HHDV mua vào:', special_line_style)
            sheet.write(y_offset, 4, '', total_line_table)
            sheet.write(y_offset, 5, 'Chỉ tiêu[24]', total_line_table)
            sheet.write(y_offset, 6, total_24 and "{:,.0f}".format(total_24) or 0, total_line_table_left_red)
            y_offset += 1

            sheet.merge_range(y_offset, 0 , y_offset, 3, 'Tổng số thuế GTGT của HHDV mua vào đủ điều kiện được khấu trừ:', special_line_style)
            sheet.write(y_offset, 4, '', total_line_table)
            sheet.write(y_offset, 5, 'Chỉ tiêu[25]', total_line_table)
            sheet.write(y_offset, 6, total_25 and "{:,.0f}".format(total_25) or 0, total_line_table_left_red)
            y_offset += 2

            sheet.merge_range(y_offset, 2 , y_offset, 6, 'Kê khai các HĐ GTGT đầu vào phát sinh trong kỳ', total_line_table_left_red)
            y_offset += 1
            sheet.merge_range(y_offset, 1 , y_offset, 7, '(Bao gồm cả các HĐ bỏ sót của kỳ trước(nếu có) - DN được KK khấu trừ trước khi CQT công bố QĐ kiểm tra tại DN)', total_line_table_left_red)
            y_offset += 1
            sheet.merge_range(y_offset, 0 , y_offset, 8, 'Hóa đơn bán hàng thông thường(không phải là hóa đơn GTGT) không nên kê vào Bảng kê hóa đơn mua vào (Theo hướng dẫn tại CV 3430/TCK-KK ngày 21/08/2014)', total_line_table_left_red)
            y_offset += 1
            sheet.merge_range(y_offset, 0 , y_offset, 8, 'Hóa đơn đầu và là hóa đơn không chịu thuế thì cũng không kê khai vào bảng kê này theo công văn 4943/TCT-CS ngày 10/11/2014', total_line_table_left_red)



    def get_lines(self,o,type):
        remove_supplier_reports = self.env.company.remove_supplier_reports
        domain = [
            ('move_id.state','=','posted'),
            ('move_id.journal_id.type','=','purchase'),
            ('move_id.date','>=',o.date_from),
            ('move_id.date','<=',o.date_to)
        ]

        if remove_supplier_reports == True:
            domain.append(('move_id.move_type', '!=', 'in_refund'))
        
        if type == 'private_use':
            domain += [('product_id.general_product','=',False),('tax_ids','!=',False),('tax_ids.type_tax_use','=','purchase')]
        if type == 'shared_use':
            domain += [('product_id.general_product','=',True),'|',('tax_ids','!=',False),('tax_ids.type_tax_use','=','purchase')]

        movelines = self.env['account.move.line'].search(domain,order="date asc")
        move_ids = movelines.mapped('move_id')

        result = []
        sum_giatri_hhdv_muavao = 0
        sum_tongsothue_gtgt_dauvao = 0
        sum_sothue_gtgt_dudk_khautru = 0

        for move in sorted(move_ids,key=lambda x:(x.date,x.name)):
            merge = []
            for line in move.line_ids:
                for tax in line.tax_ids:
                    merge.append(tax)

            for me in set(merge):
                move_thue = move.line_ids.filtered(lambda x: me.id in x.tax_ids.ids)

                giatri_hhdv_muavao = sum(move_thue.mapped('debit')) - sum(move_thue.mapped('credit'))

                account = me.invoice_repartition_line_ids.mapped('account_id').ids
                tags = me.invoice_repartition_line_ids.mapped('tag_ids').ids

                move_thue = move.line_ids.filtered(lambda x: x.account_id and x.account_id.is_vat_account and x.account_id.id in account and self.check_tag(x.tax_tag_ids,tags) == True)
                tongsothue_gtgt_dauvao = sothue_gtgt_dudk_khautru = sum(move_thue.mapped('debit')) - sum(move_thue.mapped('credit'))
                
                thue = sum(move_thue.mapped('credit')) - sum(move_thue.mapped('debit'))

                sum_giatri_hhdv_muavao += giatri_hhdv_muavao
                sum_tongsothue_gtgt_dauvao += tongsothue_gtgt_dauvao
                sum_sothue_gtgt_dudk_khautru += sothue_gtgt_dudk_khautru

                vals = {
                    'stt':0,
                    'ma_so':move.name,
                    'ngay': move.date and move.date.strftime('%d/%m/%Y') or '',
                    'nguoiban': move.partner_id.name or '',
                    'msthue': move.partner_id.vat or '',
                    'giatri_hhdv_muavao':giatri_hhdv_muavao or 0,
                    'tongsothue_gtgt_dauvao':tongsothue_gtgt_dauvao or 0,
                    'sothue_gtgt_dudk_khautru': sothue_gtgt_dudk_khautru or 0,
                    'ghichu': '',
                    'type': 'line'
                }
                result.append(vals)

        result.append({
            'stt': '',
            'ma_so': '',
            'ngay': '',
            'nguoiban': 'Tổng',
            'msthue': '',
            'giatri_hhdv_muavao': sum_giatri_hhdv_muavao or 0,
            'tongsothue_gtgt_dauvao': sum_tongsothue_gtgt_dauvao or 0,
            'sothue_gtgt_dudk_khautru': sum_sothue_gtgt_dudk_khautru or 0,
            'ghichu': '',
            'type': 'total'
        })

        return result



    def check_tag(self,tax_ids,tags):
        if any(tax.id in tags for tax in tax_ids):
            return True

        return False
    






   


        










            
            