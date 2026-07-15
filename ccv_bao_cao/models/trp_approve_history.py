# -*- coding: utf-8 -*-

from odoo import fields, models


class TrpApproveHistory(models.Model):
    _inherit = 'trp.approve.history'

    rp_production_report_id = fields.Many2one(
        'rp.production.report',
        string='Phiếu Báo cáo sản lượng')
    rp_thu_tien_report_id = fields.Many2one(
        'rp.thu.tien.report',
        string='Phiếu Báo cáo thu tiền PKD')
