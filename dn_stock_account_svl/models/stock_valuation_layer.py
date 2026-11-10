# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class StockValuationLayer(models.Model):
    """Stock Valuation Layer for tracking inventory valuation movements,
    including receipt, delivery, and internal transfers across valuation accounts.
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
        store=True,
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
    date = fields.Datetime(
        'Date',
        default=fields.Datetime.now,
        required=True,
        index=True,
    )

    def _validate_accounting_entries(self):
        """Validate accounting entries for valuation layers in batch."""
        am_vals_list = []
        for svl in self:
            if svl.product_id.valuation != 'real_time':
                continue
            if svl.currency_id.is_zero(svl.value):
                continue
            move = svl.stock_move_id
            if not move:
                continue
            entry_vals = move._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
            if entry_vals:
                if isinstance(entry_vals, list):
                    am_vals_list.extend(entry_vals)
                else:
                    am_vals_list.append(entry_vals)

        if am_vals_list:
            account_moves = self.env['account.move'].sudo().create(am_vals_list)
            account_moves.sudo().action_post()
            for account_move in account_moves:
                if account_move.stock_move_id:
                    account_move.stock_move_id.sudo().write({'account_move_id': account_move.id})
                if account_move.stock_valuation_layer_ids:
                    account_move.stock_valuation_layer_ids.sudo().write({'account_move_id': account_move.id})

    def action_dn_view_account_move(self):
        """Return an act_window action to view the associated journal entry."""
        self.ensure_one()
        if not self.account_move_id:
            return {}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.account_move_id.id,
        }
