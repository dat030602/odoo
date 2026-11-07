# -*- coding: utf-8 -*-
"""Partner model extension for Hetian RFQ Excel Template."""

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_studio_material_quality_standards = fields.Text(
        string='Material Quality Standards',
        default="""Hetian Jade & Alloy Grade A Material Specification.
Tolerance limit: +/- 0.02mm.
Certified compliance under ISO 9001:2015 and RoHS directive.""",
        help='Material quality specification referenced in Excel template (${fields.x_customer_id.x_studio_material_quality_standards})',
    )
