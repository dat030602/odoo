# -*- coding: utf-8 -*-
from odoo import models, api


class DetailsInternalTfBookPDF(models.AbstractModel):
    _name = 'report.biz_details_purchase_report.int_tf_pdf'
    _description = 'Sổ chi tiết nhập hàng tại cảng (PDF)'

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
        docs = self.env['details.internal.tf.book'].browse(docids)
        return {
            'doc_ids': docids,
            'docs': docs,
            'doc_model': 'details.internal.tf.book',
            'format_float_number': self.format_float_number,
        }
