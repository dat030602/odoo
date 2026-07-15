# -*- coding: utf-8 -*-
from odoo import models, api, _
from datetime import datetime
import base64
import io
import re
import html2text
from bs4 import BeautifulSoup
from datetime import timedelta

class ReportDetailsSalesBookByCustomerpPDF(models.AbstractModel):
    _name = 'report.biz_details_sales_book_by_customer.details_book_pdf'
    _description = 'Report Details Sales Book By Customer PDF'
    _inherit = 'report.report_xlsx.abstract'

    def format_float_number(self, num, f_covert=False):
        if not num and not f_covert:
            return 0
        number = float(num)
        if f_covert:
            formatted = "{:,.3f}".format(number)
        else:
            if number % 1 == 0:
                formatted = "{:,.0f}".format(number)
            else:
                formatted = "{:,.2f}".format(number).rstrip('0')
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".") #format lại theo hàng 
        return formatted

    def get_reason_output_input_stock(self, reason_output_input_stock):
        if reason_output_input_stock:
            # soup = BeautifulSoup(reason_output_input_stock, 'html.parser')
            # return soup.get_text()
            soup = BeautifulSoup(reason_output_input_stock, 'lxml')
            soup_format = soup.prettify()
            html2_text = html2text.html2text(soup_format)
            clean_note = re.sub(r'[^\w\s,\-]', '', html2_text)
            clean_note = '\n'.join([line.strip() for line in clean_note.splitlines() if line.strip()])
            return clean_note.strip()
        return ''

    @api.model
    def _get_report_values(self, docids, data=None):
        self = self.sudo().with_context(lang='vi_VN')
        doc = self.env['details.sales.book.by.customer'].browse(docids)
        return {
            'doc_ids': docids,
            'docs':doc,
            'doc_model': 'details.sales.book.by.customer',
            'format_float_number': self.format_float_number,
        }