# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import html2plaintext

 
class ccv_warehouse_transfer_note(models.AbstractModel):
    _name = 'report.biz_ccv_sale.report_business_pdf'
    _description = 'ccv_warehouse_transfer_note'

    def format_decimal(self, number):
        if not number:
            return 0
        string = '{:,.3f}'.format(number).split('.')
        return '%s,%s' % (string[0].replace(',','.'), string[1])

    @api.model
    def _get_report_values(self, docids, data=None):
        # Tra ve danh sach tung record rieng le thay vi 1 recordset lon
        # De XML wrapper (report_business_pdf) co the lap qua tung doc mot
        docs = [self.env['stock.picking'].browse(docid).sudo() for docid in docids]
        return {
            'doc_ids': docids,
            'docs': docs,
            'doc_model': 'stock.picking',
            'format_decimal': self.format_decimal
        }