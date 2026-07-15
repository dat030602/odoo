# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from datetime import datetime
from odoo.addons.biz_delegate_expense_mbbank.config import amount_to_text

class DelegateExpense(models.AbstractModel):
    _name = 'report.biz_delegate_expense_mbbank.delegate_expense_mb_template'
    _description = 'Delegate Expense MB Template'
    
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
    
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.payment'].sudo().browse(docids)
        return {
            'doc_ids': docids,
            'docs': docs,
            # 'doc_model': 'sale.order',
            # 'get_formatted_wedding_day': self.get_formatted_wedding_day,
            'format_float_number': self.format_float_number,
            # 'get_journal_type_display': self.get_journal_type_display,
            # 'format_date_vn': self.format_date_vn,
            'amount2text': self.amount2text,
        }