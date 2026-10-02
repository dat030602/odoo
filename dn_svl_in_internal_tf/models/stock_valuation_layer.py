# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockValuationLayer(models.Model):
    """Stock Valuation Layer for tracking inventory valuation movements,
    including internal transfers between different valuation accounts.
    """
    _name = 'stock.valuation.layer'
    _description = 'Stock Valuation Layer'
    _order = 'create_date desc, id desc'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        index=True,
        ondelete='cascade',
    )
    quantity = fields.Float('Quantity', help='Quantity')
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )
    unit_cost = fields.Monetary('Unit Value', currency_field='currency_id')
    value = fields.Monetary('Total Value', currency_field='currency_id')
    remaining_qty = fields.Float('Remaining Qty')
    remaining_value = fields.Monetary('Remaining Value', currency_field='currency_id')
    description = fields.Char('Description')
    stock_move_id = fields.Many2one(
        'stock.move',
        string='Stock Move',
        index=True,
        ondelete='cascade',
    )
    account_move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        index=True,
        ondelete='set null',
    )
