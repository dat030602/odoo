# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from datetime import datetime
from odoo.addons.biz_accounting_voucher_ccv.config import amount_to_text

class InternalTransferAccountingVoucher(models.AbstractModel):
    _name = 'report.biz_internal_transfer_slip_ccv.report_i_t_a_v'
    _description = 'Account Payment Slip'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.payment'].sudo().browse(docids)
        return {
            'doc_ids': docids,
            'docs': docs,
            'amount_to_text': amount_to_text,
        }