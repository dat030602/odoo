# -*- coding: utf-8 -*-
from odoo import models, api, _
from datetime import datetime, date
import base64
import io

class DetailsPurchaseReportPDF(models.AbstractModel):
    _name = 'report.biz_details_purchase_report.details_purchase_report_pdf'
    _description = 'Details Purchase Report PDF'
    _inherit = 'report.report_xlsx.abstract'
    
    
    def get_lines(self,o):
        StockMove = self.env['stock.move'].sudo()
        domain = [('purchase_line_id', '!=', False), ('location_id.usage', '=', 'supplier'), ('state', '=', 'done')]
        if o.date_from:
            domain.append(('date','>=', o.date_from))
        if o.date_to:
            domain.append(('date','<=', o.date_to))
        if o.warehouse_ids:
            domain += ['|',('location_id.warehouse_id', 'in', o.warehouse_ids.ids), ('location_dest_id.warehouse_id', 'in', o.warehouse_ids.ids)]
        result = {}
        StockMoves = StockMove.search(domain, order='date asc')
        page = 1
        stt = 0
        res = result.setdefault(page, {
            'lines': [],
            'sum_quantity': 0,
            'sum_purchase_value_nt': 0,
            'sum_purchase_value': 0
        })
        for line in StockMoves:
            stt += 1
            res = result.setdefault(page, {
                'lines': [],
                'sum_quantity': 0,
                'sum_purchase_value_nt': 0,
                'sum_purchase_value': 0
            })
               
            quantity = line.quantity_done or 0
            purchase_line = line.purchase_line_id
            order = purchase_line.order_id if purchase_line else False
            invoice_lines = purchase_line.invoice_lines if purchase_line else False
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
                
            res['lines'].append({
                'stt': stt,
                'date': line.date or '',
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
            res['sum_quantity'] += quantity
            res['sum_purchase_value_nt'] += unit_price_nt * quantity
            res['sum_purchase_value'] += purchase_value
            if stt % 7 ==0:
                page+=1
                
        return result

    def format_float_number(self, num):
        if not num:
            return 0

        number = float(num)
        if number % 1 == 0:
            return "{:,.0f}".format(number)
        else:
            number_format = "{:,.3f}".format(number)
            return number_format
    
    @api.model
    def _get_report_values(self, docids, data=None):
        self = self.sudo().with_context(lang='vi_VN')
        doc = self.env['wz.select.time.report'].browse(docids)
        return {
            'doc_ids': docids,
            'docs':doc,
            'doc_model': 'wz.select.time.report',
            'format_float_number': self.format_float_number,
            'get_lines':self.get_lines,
        }