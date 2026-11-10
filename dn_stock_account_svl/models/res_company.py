# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    svl_modification_mode = fields.Selection(
        selection=[
            ('create_diff', 'Create Adjustment Layers & Journal Entries'),
            ('update_existing', 'Update Existing Layers & Adjust Journal Entries'),
        ],
        string='Valuation Modification Mode',
        default='create_diff',
        required=True,
        help='Method used when modifying completed stock move quantities: create compensatory SVLs and JEs, or directly update existing ones.',
    )
    svl_modification_date_mode = fields.Selection(
        selection=[
            ('current_date', 'Current Date'),
            ('picking_date', 'Picking Done Date'),
        ],
        string='Valuation Modification Date Mode',
        default='current_date',
        required=True,
        help='Accounting date to assign when adjusting valuation of completed moves.',
    )
    svl_decrease_cost_basis = fields.Selection(
        selection=[
            ('current_standard_price', 'Current Standard Price'),
            ('original_layer', 'Original Layer Cost'),
        ],
        string='Decrease Quantity Cost Basis',
        default='current_standard_price',
        required=True,
        help='Cost basis used when decreasing completed stock move quantities in adjustment mode.',
    )
