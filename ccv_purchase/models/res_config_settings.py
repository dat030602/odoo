# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_chief_accountant_id = fields.Many2one(
        'res.users',
        string='Kế toán trưởng',
        default_model='purchase.order',
    )
    default_unit_head_id = fields.Many2one(
        'res.users',
        string='Thủ trưởng đơn vị',
        default_model='purchase.order',
    )
