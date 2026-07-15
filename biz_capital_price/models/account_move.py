# -*- coding: utf-8 -*-

from odoo import fields, models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    average_period_id = fields.Many2one("average.capital.price.end.period", index=True)
    internal_svl_ids = fields.One2many("stock.valuation.layer", 'interval_move_id', 'Layers')
    carryover_mass_period_ids = fields.One2many("average.price.end.period.mass", 'carryover_move_id', string="Carryover Mass Period")

    def action_update_cost_layer(self):
        for move in self:
            debit = sum(move.line_ids.mapped('debit'))
            if not debit:
                continue  # Skip processing if debit is zero or not set
            layers = self.env['stock.valuation.layer'].search([
                ('account_move_id', '=', move.id)
            ])
            for layer in layers:
                layer.value = debit
                layer.unit_cost = debit / layer.quantity if layer.quantity else 0