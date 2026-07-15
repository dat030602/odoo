# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    large_amount_warning_threshold = fields.Boolean(
        'Large Amount Warning Threshold')
    threshold_amount = fields.Monetary(
        'Threshold Amount',
        currency_field='currency_id')
