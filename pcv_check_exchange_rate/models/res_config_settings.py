# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    large_amount_warning_threshold = fields.Boolean(
        'Large Amount Warning Threshold',
        related='company_id.large_amount_warning_threshold', readonly=False)
    threshold_amount = fields.Monetary(
        'Threshold Amount',
        related='company_id.threshold_amount',
        currency_field='company_currency_id',
        readonly=False)
