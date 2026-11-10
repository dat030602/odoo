# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_svl_move_type_ids = fields.Many2many(
        'stock.valuation.move.type',
        'company_auto_svl_move_type_rel',
        string='Auto Create Valuation Layers',
    )
    auto_je_move_type_ids = fields.Many2many(
        'stock.valuation.move.type',
        'company_auto_je_move_type_rel',
        string='Auto Create Journal Entries',
    )

    @api.constrains('auto_svl_move_type_ids', 'auto_je_move_type_ids')
    def _check_auto_valuation_move_types(self):
        for company in self:
            invalid = company.auto_je_move_type_ids - company.auto_svl_move_type_ids
            if invalid:
                raise ValidationError(
                    _("If Journal Entry creation is enabled for a move type (%s), "
                      "Stock Valuation Layer (SVL) creation must also be enabled for it.")
                    % ", ".join(invalid.mapped('name'))
                )
