# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_move_id = fields.Many2one(
        'stock.move',
        string='Stock Move',
        index='btree_not_null',
    )
    stock_valuation_layer_ids = fields.One2many(
        'stock.valuation.layer',
        'account_move_id',
        string='Stock Valuation Layers',
    )
    dn_svl_count = fields.Integer(
        string='Valuation Layers',
        compute='_compute_dn_svl_count',
    )

    def _compute_dn_svl_count(self):
        for move in self:
            move.dn_svl_count = len(move.sudo().stock_valuation_layer_ids)

    def action_dn_view_svl(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Valuation Layers'),
            'res_model': 'stock.valuation.layer',
            'view_mode': 'list,form',
            'domain': [('account_move_id', '=', self.id)],
        }

    def action_dn_view_stock_moves(self):
        self.ensure_one()
        domain = [('account_move_id', '=', self.id)]
        if self.stock_move_id:
            domain = ['|', ('id', '=', self.stock_move_id.id), ('account_move_id', '=', self.id)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Moves'),
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': domain,
        }
