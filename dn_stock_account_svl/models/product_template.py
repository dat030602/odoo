# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    use_location_valuation_account = fields.Boolean(
        string='Use Location Valuation Account',
        default=False,
        help='If checked, inventory valuation entries for this product prioritize the valuation account configured on the stock location instead of the product category.',
    )
