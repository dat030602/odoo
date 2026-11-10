# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    svl_modification_mode = fields.Selection(
        related='company_id.svl_modification_mode',
        readonly=False,
        string='Valuation Modification Mode',
    )
    svl_modification_date_mode = fields.Selection(
        related='company_id.svl_modification_date_mode',
        readonly=False,
        string='Valuation Modification Date Mode',
    )
    svl_decrease_cost_basis = fields.Selection(
        related='company_id.svl_decrease_cost_basis',
        readonly=False,
        string='Decrease Quantity Cost Basis',
    )
