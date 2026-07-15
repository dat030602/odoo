# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from datetime import datetime
from odoo.addons.biz_accounting_voucher_ccv.config import amount_to_text

def get_address(partner_id):
    if not partner_id:
        return ''
    address_parts = []
    
    if partner_id.street:
        address_parts.append(partner_id.street)
    
    if partner_id.wards_id:
        address_parts.append(partner_id.wards_id.name) 
    
    if partner_id.district_id:
        address_parts.append(partner_id.district_id.name)
    
    if partner_id.state_id:
        address_parts.append(partner_id.state_id.name)
    
    if partner_id.country_id:
        address_parts.append(partner_id.country_id.name)

    full_address = ', '.join(address_parts)
    return full_address

class DelegateExpense(models.AbstractModel):
    _name = 'report.biz_account_payment_slip_ccv.payment_slip_template'
    _description = 'Account Payment Slip'
    
    def amount2text(self, number, integer=False):
        if integer:
            return amount_to_text(number).split(' đồng')[0].lower()
        return amount_to_text(number)
    
    def format_float_number(self, number):
        number_format = ''
        if number:
            if number % 1 == 0:
                number_format = "{:,.0f}".format(number).replace(',', '.')
            else:
                number_format = "{:,.2f}".format(number).rstrip('0').replace(',', '.')
        return number_format
    
    def get_lines(self, move):
        lines = {}
        for line in move.line_ids:
            account = line.account_id.code
            if '/' not in lines:
                lines['/'] = {
                    'name': line.name,
                    'debit': line.debit > 0 and [account] or [],
                    'credit': line.credit > 0 and [account] or [],
                    'amount': line.debit > 0 and line.debit or 0
                }
            else:
                if line.debit > 0:
                    if account not in lines['/']['debit']:
                        lines['/']['debit'].append(account)
                    
                    lines['/']['amount'] += line.debit
                
                if line.credit > 0:
                    if account not in lines['/']['credit']:
                        lines['/']['credit'].append(account)
       
        for line in lines.values():
            line['debit'] = ','.join(line['debit'])
            line['credit'] = ','.join(line['credit'])

        return lines.values()
    
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.payment'].sudo().browse(docids)
        return {
            'doc_ids': docids,
            'docs': docs,
            'format_float_number': self.format_float_number,
            'amount2text': self.amount2text,
            'get_lines': self.get_lines,
            'get_address': get_address
        }