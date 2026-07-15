# -*- coding: utf-8 -*-
from odoo import fields, models

class TrpApproveHistory(models.Model):
    _inherit = 'trp.approve.history'

    summary_output_daily_work_id = fields.Many2one('summary.output.daily.work', string='Tổng hợp sản lượng công nhân')
