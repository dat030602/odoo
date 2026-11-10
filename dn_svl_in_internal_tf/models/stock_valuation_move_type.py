# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockValuationMoveType(models.Model):
    """Model to define stock move types eligible for automated valuation and journal entries."""

    _name = 'stock.valuation.move.type'
    _description = 'Stock Valuation Move Type'
    _order = 'id'

    name = fields.Char(string='Name', required=True, translate=True)
    key = fields.Char(string='Key', required=True, index=True)
