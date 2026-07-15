# -*- coding: utf-8 -*-
from odoo import models, api


class DetailsStockOrderBookPDF(models.AbstractModel):
    _name = 'report.biz_details_purchase_report.stock_order_book_pdf'
    _description = 'Báo cáo hàng tồn kho khu vực (PDF)'

    def format_float_number(self, num):
        if not num:
            return 0
        number = float(num)
        if number % 1 == 0:
            return "{:,.0f}".format(number)
        else:
            return "{:,.3f}".format(number)

    @api.model
    def _get_report_values(self, docids, data=None):
        self = self.sudo().with_context(lang='vi_VN')
        docs = self.env['details.stock.order.book'].browse(docids)
        
        doc_data = {}
        for doc in docs:
            # Group lines by team_id
            groups = {}
            # Sort lines: Teams with names first, 'No Team' (False) last
            sorted_lines = doc.line_ids.sorted(key=lambda l: (not l.team_id, l.team_id.name or '', l.id))
            for line in sorted_lines:
                team = line.team_id
                if team not in groups:
                    groups[team] = self.env['details.stock.order.book.line']
                groups[team] |= line
            doc_data[doc.id] = groups

        return {
            'doc_ids': docids,
            'docs': docs,
            'doc_model': 'details.stock.order.book',
            'doc_groups': doc_data, # Pass grouped data
            'format_float_number': self.format_float_number,
        }
