# -*- coding: utf-8 -*-
from odoo import models, api, _
from datetime import datetime, date


class InventoryReportPdf(models.AbstractModel):
    _name = 'report.biz_inventory_report.inventory_report_pdf'
    _description = 'Inventory Report PDF'

    def get_inventory_time(self, docs):
        dates = [doc.last_count_date for doc in docs]
        max_date = max(dates)
        return "Ngày %s tháng %s năm %s" % ( max_date.day, max_date.month, max_date.year)
    
    def convert_print(self, value):
        if not value:
            return ''
        if str(value).find('202') > -1:
            return str(value).split('-')[2] + '/' + str(value).split('-')[1] + '/' + str(value).split('-')[0]

        return value

    def convert_vnd(self, amount):
        a = format(amount, ',.0f')
        return a

    def convert_number(self, amount):
        number = str(round(amount, 3))
        if number.find('.') > -1:
            number = number.split('.')
            head = number[0]
            tail = number[1]
            if len(tail) == 1:
                number = head + '.' + tail + '00'
            elif len(tail) == 2:
                number = head + '.' + tail + '0'
            else:
                number = head + '.' + tail
        else:
            number = number + '.000'
        return number
    
    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env['stock.quant']
        docs = model.browse(docids)
        return {
            'doc_ids': docids,
            'docs':docs,
            'doc_model': model,
            'convert_print': self.convert_print,
            'convert_vnd': self.convert_vnd,
            'convert_number': self.convert_number,
            'get_inventory_time': self.get_inventory_time,
        }