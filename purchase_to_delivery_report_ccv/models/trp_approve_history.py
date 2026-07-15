# -*- coding: utf-8 -*-
from odoo import fields, models

class TrpApproveHistory(models.Model):
    _inherit = 'trp.approve.history'

    export_delivery_report_id = fields.Many2one('export.delivery.report.ccv', string='Báo cáo chốt lô nguyên liệu')
