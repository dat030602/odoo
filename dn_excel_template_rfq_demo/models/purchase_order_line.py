# -*- coding: utf-8 -*-
"""Purchase Order Line model extension for Hetian RFQ Excel Template."""

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    order_number = fields.Char(
        string='Order Number',
        default='ORD-HT-2026',
        help='Order item identifier referenced in Excel template (${table:summary.order_number})',
    )
    design = fields.Char(
        string='Design Code',
        default='BSK-HT-SPEC-01',
        help='Design specification code referenced in Excel template (${table:summary.design})',
    )
