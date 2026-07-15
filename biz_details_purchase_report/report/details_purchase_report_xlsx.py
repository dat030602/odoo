# -*- coding: utf-8 -*-
from odoo import models, _
from datetime import datetime, date
import base64
import io
import logging
_logger = logging.getLogger(__name__)

class DetailsPurchaseReportXlsx(models.AbstractModel):
    _name = 'report.biz_details_purchase_report.details_purchase_report_xlsx'
    _description = 'Details Purchase Report Xlsx'
    _inherit = 'report.report_xlsx.abstract'
    
    def generate_xlsx_report(self, workbook, data, details):
        self = self.with_context(lang=self.env.user.lang)
        for o in details:
            company_id = self.env.company
            def get_format(*arguments):
                normal_style = {'font_name': 'Times New Roman', 'font_size': 12, 'valign': 'vcenter', 'align': 'left'}
                for arg in arguments:
                    normal_style.update(arg)
                return workbook.add_format(normal_style)
            report_title = {'bold': True, 'font_size': 16, 'text_wrap': True, 'align': 'center'}
            sub_title_format = {'font_size': 13, 'text_wrap': True, 'align': 'center','bold': True}
            signature_style = workbook.add_format({'italic': True,'font_name': 'Times New Roman', 'font_size': 12, 'valign':'vcenter','align': 'center',})
            
            worksheet_name = _(f"Details purchase report")
            sheet = workbook.add_worksheet(worksheet_name)
            
            sheet.set_column(0,1,5)
            sheet.set_column(1,2,10)
            sheet.set_column(3,3,25)
            sheet.set_column(4,4,15)
            sheet.set_column(5,6,15)
            sheet.set_column(7,8,8)
            sheet.set_column(9,9,10)
            sheet.set_column(10,10,10)
            sheet.set_column(11,12,10)    
            sheet.set_column(11,12,10)    
            sheet.set_column(13,16,10)    
        
            y_offset = 0
            
            image = company_id.logo or False
            sheet.set_row(y_offset, 55)
            if image:
                image_data = io.BytesIO(base64.b64decode(image)) 
                sheet.insert_image(y_offset, 0, image, {'image_data': image_data, 'x_scale': 0.2, 'y_scale': 0.2, 'x_offset': 0, 'y_offset': 0})
                sheet.merge_range(y_offset, 0, y_offset, 6,  '                   ' +company_id.name + ' - Mã số thuế:' +  company_id.vat , get_format({'align': 'left',  'font_size': 15, 'left': 10}))
            y_offset +=1
            sheet.merge_range(y_offset, 0, y_offset, 16, "SỔ CHI TIẾT MUA HÀNG", get_format(report_title))
            y_offset +=1
            from_date = ''
            to_date = ''
            if o.date_from:
                from_date = o.date_from.strftime('%d/%m/%Y')
            if o.date_to:
                to_date = o.date_to.strftime('%d/%m/%Y')
            sub_title = 'Từ ngày %s đến ngày %s' % (from_date, to_date)
            sheet.merge_range(y_offset, 0, y_offset , 16, sub_title, get_format(sub_title_format, {'italic': True}))
            y_offset +=1
            sheet.write(y_offset, 0, 'STT', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 1, 'Ngày chứng từ', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 2, 'Số chứng từ', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 3, 'Tên nhà cung cấp', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 4, 'Mã hàng', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 5, 'Tên hàng', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 6, 'ĐVT', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 7, 'Số lượng mua', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 8, 'Tỷ giá', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 9, 'Đơn giá NT', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 10, 'Đơn giá', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 11, 'Giá trị mua NT', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 12, 'Giá trị mua', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 13, 'Mã kho', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 14, 'TK Nợ', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 15, 'TK Có', get_format({'bold': True, 'align': 'center'}))
            sheet.write(y_offset, 16, 'Đơn mua hàng', get_format({'bold': True, 'align': 'center'}))
            y_offset += 1
                
            lines, sum_quantity, sum_purchase_value_nt, sum_purchase_value = self.get_lines(o)
            for line in lines: 
                sheet.write(y_offset, 0, line.get('stt'), get_format({'align': 'center'}))
                sheet.write(y_offset, 1, line.get('date'), get_format({'align': 'center'}))
                sheet.write(y_offset, 2, line.get('name'), get_format({'align': 'left', 'color': '#0000FF'}))
                sheet.write(y_offset, 3, line.get('partner_name'), get_format({'align': 'left'}))
                sheet.write(y_offset, 4, line.get('product_code'), get_format({'align': 'left'}))
                sheet.write(y_offset, 5, line.get('product_name'), get_format({'align': 'left'}))
                sheet.write(y_offset, 6, line.get('product_uom_id'), get_format({'align': 'left'}))
                sheet.write(y_offset, 7, line.get('quantity'), get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 8, line.get('exchange_rate'), get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 9, line.get('unit_price_nt'), get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 10, line.get('unit_price'), get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 11, line.get('purchase_value_nt'), get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 12, line.get('purchase_value'), get_format({'align': 'right', 'num_format': '#,##0.000'}))
                sheet.write(y_offset, 13, line.get('location_dest_id'), get_format({'align': 'left'}))
                sheet.write(y_offset, 14, line.get('account_debit'), get_format({'align': 'left'}))
                sheet.write(y_offset, 15, line.get('account_credit'), get_format({'align': 'left'}))
                sheet.write(y_offset, 16, line.get('order_name'), get_format({'align': 'left'}))
                y_offset += 1
                              
            sheet.merge_range(y_offset, 0, y_offset, 6, 'Tổng cộng', get_format(({'align': 'left','bold': True})))
            sheet.write(y_offset, 7, self.format_float_number(sum_quantity), get_format({'align': 'right', 'bold': True}))
            sheet.write(y_offset, 8, '', get_format())
            sheet.write(y_offset, 9, '', get_format())
            sheet.write(y_offset, 10, '', get_format())
            sheet.write(y_offset, 11, self.format_float_number(sum_purchase_value_nt), get_format({'align': 'right', 'bold': True}))
            sheet.write(y_offset, 12, self.format_float_number(sum_purchase_value), get_format({'align': 'right', 'bold': True}))
            sheet.write(y_offset, 13, '', get_format())
            sheet.write(y_offset, 14, '', get_format())
            sheet.write(y_offset, 15, '', get_format())
            sheet.write(y_offset, 16, '', get_format())
            y_offset += 2
                    
            # sheet.write(y_offset, 16, str(page) + '/' + str(lines_count), get_format({'align': 'right','font_size': 10}))
            # y_offset += 2
            sheet.merge_range(y_offset,14,y_offset,16, 'Ngày ... tháng ... năm .......', get_format({'align': 'center', 'italic': True}))
            y_offset += 1
            
            sheet.merge_range(y_offset,0,y_offset,4, 'Người lập biểu', get_format({'bold': True,'align': 'center'}))
            sheet.merge_range(y_offset,5,y_offset,9, 'Kế toán trưởng',  get_format({'bold': True,'align': 'center'}))
            sheet.merge_range(y_offset,10,y_offset,16, 'Thủ trưởng đơn vị',  get_format({'bold': True,'align': 'center'}))

            y_offset += 1
            sheet.merge_range(y_offset,0,y_offset,4, '(Ký, họ tên)', signature_style)
            sheet.merge_range(y_offset,5,y_offset,9, '(Ký, họ tên)', signature_style)
            sheet.merge_range(y_offset,10,y_offset,16, '(Ký, họ tên, đóng dấu)', signature_style)
            
            y_offset += 5   
            sheet.merge_range(y_offset,0,y_offset,4, o.creator_id.name_without_position or '', get_format({'bold': True,'align': 'center'}))
            sheet.merge_range(y_offset,5,y_offset,9, o.accountant_chief_id.name_without_position  or '', get_format({'bold': True,'align': 'center'}))
            sheet.merge_range(y_offset,10,y_offset,16, o.unit_head_id.name_without_position or '', get_format({'bold': True,'align': 'center'}))

    def get_lines(self,o):
        StockMove = self.env['stock.move'].sudo()
        domain = [('purchase_line_id', '!=', False), ('location_id.usage', '=', 'supplier'), ('state', '=', 'done')]
        if o.date_from:
            domain.append(('date','>=', o.date_from))
        if o.date_to:
            domain.append(('date','<=', o.date_to))
        if o.warehouse_ids:
            domain += ['|',('location_id.warehouse_id', 'in', o.warehouse_ids.ids), ('location_dest_id.warehouse_id', 'in', o.warehouse_ids.ids)]
        result = []
        StockMoves = StockMove.search(domain, order='date asc')
        stt = sum_quantity = sum_purchase_value_nt = sum_purchase_value = 0
        for line in StockMoves:
            stt += 1
            quantity = line.quantity_done or 0
            purchase_line = line.purchase_line_id
            order = purchase_line.order_id if purchase_line else False
            invoice_lines = purchase_line.invoice_lines.filtered(lambda l:l.move_id.move_type == 'in_invoice')
            move_ids = self.env['account.move']
            for move in invoice_lines.move_id:
                if not any([True for line in move.line_ids if line.account_id.account_type in ['expense', 'expense_depreciation','expense_direct_cost']]):
                    move_ids |= move
            invoice_lines = move_ids.line_ids.filtered(lambda l: l in purchase_line.invoice_lines)
            currency = order.currency_id if order else False
            currency_name = currency.name if currency else ''
            exchange_rate = unit_price_nt = unit_price = purchase_value = purchase_value_nt = 0
            account_debit = ''
            account_credit = ''
            
            if purchase_line:
                price_unit = purchase_line.price_unit
                if currency_name == 'VND':
                    unit_price = price_unit
                    purchase_value_nt = unit_price_nt * quantity
                    purchase_value = unit_price * quantity
                else:
                    unit_price_nt = price_unit
                    purchase_value_nt = unit_price_nt * quantity
                    if order and order.apply_manual_currency_exchange:
                        exchange_rate = order.inverse_manural_currency_exchange_rate    
                    else:
                        date_approve = order.date_approve and order.date_approve.date() or False
                        if date_approve:
                            #lấy tỷ giá gần nhất
                            rate_before = currency.rate_ids.filtered(lambda r: r.name <= date_approve).sorted('name', reverse=True)[:1]
                            if rate_before:
                                exchange_rate = rate_before.inverse_company_rate
                    unit_price = unit_price_nt * exchange_rate
                    purchase_value = purchase_value_nt * exchange_rate
            
            if invoice_lines:
                account_debit = invoice_lines.mapped('account_id.code')[0] or ''
                account_credit = invoice_lines.mapped('ctp_account_ids.code')[0] if invoice_lines.mapped('ctp_account_ids.code') else ''
            else:
                account_move_ids = line.account_move_ids.filtered(lambda x: x.state == 'posted') 
                line_debit_ids = account_move_ids.line_ids.filtered(lambda x: x.debit > 0) 
                line_credit_ids = account_move_ids.line_ids.filtered(lambda x: x.credit > 0) 
                account_debit = line_debit_ids.mapped('account_id.code')[0] if line_debit_ids else ''
                account_credit = line_credit_ids.mapped('account_id.code')[0] if line_credit_ids else ''
            
            result.append({
                'stt': stt,
                'date': line.date and line.date.strftime('%d/%m/%Y') or '',
                'name': line.reference and line.reference or '',
                'partner_name': purchase_line and purchase_line.partner_id.name or '',
                'product_code': line.product_id and line.product_id.code or '',
                'product_name': line.product_id and line.product_id.name or '',
                'product_uom_id': line.product_uom and line.product_uom.name.upper() or '',
                'quantity': quantity,
                'exchange_rate': exchange_rate,
                'unit_price_nt': unit_price_nt,
                'unit_price': unit_price,
                'purchase_value_nt': purchase_value_nt,
                'purchase_value': purchase_value,
                'location_dest_id': line.location_dest_id and line.location_dest_id.location_id.name or '',
                'account_debit': account_debit,
                'account_credit': account_credit,
                'order_name': line.origin or '',
            })
            sum_quantity += quantity
            sum_purchase_value_nt += unit_price_nt * quantity
            sum_purchase_value += purchase_value
          
        return result, sum_quantity, sum_purchase_value_nt, sum_purchase_value

    def format_float_number(self, num):
        if not num:
            return 0

        number = float(num)
        if number % 1 == 0:
            return "{:,.0f}".format(number)
        else:
            number_format = "{:,.3f}".format(number)
            return number_format