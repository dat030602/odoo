# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _should_exclude_for_valuation(self):
        """Hook to exclude certain lines from valuation if needed."""
        self.ensure_one()
        return False

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if self.env.context.get('skip_valuation_adjust'):
            return lines

        moves_to_adjust = lines.mapped('move_id').filtered(
            lambda m: m.state == 'done' and m.product_id.is_storable and m.product_id.valuation == 'real_time'
        )
        for move in moves_to_adjust:
            old_qty = move.product_qty - sum(
                l.quantity_product_uom for l in lines.filtered(lambda l: l.move_id == move)
            )
            new_qty = move.product_qty
            if old_qty != new_qty:
                move.with_context(skip_valuation_adjust=True)._handle_valuation_quantity_change(
                    old_qty, new_qty
                )
        return lines

    def write(self, vals):
        if self.env.context.get('skip_valuation_adjust') or 'quantity' not in vals:
            return super().write(vals)

        old_data = {
            line.id: (line.move_id, line.quantity_product_uom)
            for line in self
            if line.move_id and line.move_id.state == 'done' and line.move_id.product_id.is_storable
        }
        res = super().write(vals)

        moves_delta = defaultdict(float)
        for line_id, (move, old_line_qty) in old_data.items():
            line = self.browse(line_id)
            if line.exists():
                moves_delta[move] += (line.quantity_product_uom - old_line_qty)

        for move, delta in moves_delta.items():
            if delta != 0.0 and move.state == 'done':
                new_qty = move.product_qty
                old_qty = new_qty - delta
                move.with_context(skip_valuation_adjust=True)._handle_valuation_quantity_change(
                    old_qty, new_qty
                )

        return res

    def unlink(self):
        if self.env.context.get('skip_valuation_adjust'):
            return super().unlink()

        old_data = {
            line.id: (line.move_id, line.quantity_product_uom)
            for line in self
            if line.move_id and line.move_id.state == 'done' and line.move_id.product_id.is_storable
        }
        res = super().unlink()

        moves_delta = defaultdict(float)
        for line_id, (move, old_line_qty) in old_data.items():
            if move.exists() and move.state == 'done':
                moves_delta[move] -= old_line_qty

        for move, delta in moves_delta.items():
            if delta != 0.0 and move.state == 'done':
                new_qty = move.product_qty
                old_qty = new_qty - delta
                move.with_context(skip_valuation_adjust=True)._handle_valuation_quantity_change(
                    old_qty, new_qty
                )

        return res
