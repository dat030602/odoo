# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Add options to configure automatic SVL and Journal Entry generation in Inventory Settings."""

    _inherit = 'res.config.settings'

    auto_svl_move_type_ids = fields.Many2many(
        related='company_id.auto_svl_move_type_ids',
        readonly=False,
        string='Valuation Layers (SVL)',
    )
    auto_je_move_type_ids = fields.Many2many(
        related='company_id.auto_je_move_type_ids',
        readonly=False,
        string='Journal Entries',
    )

    @api.onchange('auto_je_move_type_ids')
    def _onchange_auto_je_move_type_ids(self):
        for record in self:
            record.auto_svl_move_type_ids |= record.auto_je_move_type_ids

    @api.onchange('auto_svl_move_type_ids')
    def _onchange_auto_svl_move_type_ids(self):
        for record in self:
            record.auto_je_move_type_ids &= record.auto_svl_move_type_ids
