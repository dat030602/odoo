# -*- coding: utf-8 -*-
from odoo import models, api

import logging
_logger = logging.getLogger(__name__)


class BaoCaoSanLuongNhapXuatPdf(models.AbstractModel):
    _name = 'report.ccv_api_connector.bao_cao_sl_nhap_xuat_pdf'
    _description = 'Báo cáo sản lượng nhập xuất PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['rp.tf.vehicel.in.out.wizard'].browse(docids)
        xlsx_report = self.env['report.ccv_api_connector.bao_cao_san_luong_nhap_xuat']
        report_data = xlsx_report._get_data_export(docs[0])
        return {
            'doc_ids': docids,
            'doc_model': 'rp.tf.vehicel.in.out.wizard',
            'docs': docs,
            'lines': report_data.get('all_lines', []),
            'grand_totals': report_data.get('grand_totals', {}),
        }
