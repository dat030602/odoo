# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    use_location_valuation_account = fields.Boolean(
        string='Use Location Valuation Account',
        compute='_compute_use_location_valuation_account',
        store=True,
        readonly=False,
        help='If checked, inventory valuation entries for this product prioritize the valuation account configured on the stock location instead of the product category.',
    )

    @api.depends('product_tmpl_id.use_location_valuation_account')
    def _compute_use_location_valuation_account(self):
        for product in self:
            product.use_location_valuation_account = product.product_tmpl_id.use_location_valuation_account
