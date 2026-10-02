# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Add an option to enable SVL generation for internal transfers in Inventory Settings."""

    _inherit = 'res.config.settings'

    group_internal_transfer_valuation = fields.Boolean(
        string='Internal Transfer Valuation',
        implied_group='dn_svl_in_internal_tf.group_internal_transfer_valuation',
        help=(
            'When enabled, the system automatically generates Stock Valuation '
            'Layers (SVL) and accounting journal entries for stock moves '
            'between two internal locations that use different valuation accounts.'
        ),
    )
