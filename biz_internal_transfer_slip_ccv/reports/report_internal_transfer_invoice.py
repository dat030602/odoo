# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from datetime import datetime
from odoo.addons.biz_accounting_voucher_ccv.config import amount_to_text

class InternalTransferAccountingVoucher(models.AbstractModel):
    _name = 'report.biz_internal_transfer_slip_ccv.i_report_i_t_a_v'
    _description = 'Account Payment Slip'
    
    def get_account_code(self, line_ids, type):
        lines = []
        if type == "debit":
            for line in line_ids:
                if line.debit > 0:
                    lines.append(line.account_id.code)
        elif type == "credit":
            for line in line_ids:
                if line.credit > 0:
                    lines.append(line.account_id.code)
        result = ', '.join(lines)
        return result
    def sum_debit(self, line_ids):
        sum = 0
        for line in line_ids:
            if line.debit > 0:
                sum += line.debit
        return sum
    
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].sudo().browse(docids)
        return {
            'doc_ids': docids,
            'docs': docs,
            'amount_to_text': amount_to_text,
            'get_account_code': self.get_account_code,
            'sum_debit': self.sum_debit,
        }