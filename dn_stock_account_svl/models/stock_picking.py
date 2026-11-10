# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    dn_account_move_count = fields.Integer(
        string='Journal Entries',
        compute='_compute_dn_account_move_count',
    )
    dn_svl_count = fields.Integer(
        string='Valuation Layers',
        compute='_compute_dn_svl_count',
    )

    def _compute_dn_account_move_count(self):
        for picking in self:
            moves = picking.move_ids
            account_moves = (
                moves.sudo().stock_valuation_layer_ids.account_move_id.filtered('id')
                | moves.account_move_id.filtered('id')
            )
            picking.dn_account_move_count = len(account_moves)

    def _compute_dn_svl_count(self):
        for picking in self:
            picking.dn_svl_count = len(picking.move_ids.sudo().stock_valuation_layer_ids)

    def action_dn_view_account_moves(self):
        self.ensure_one()
        moves = self.move_ids
        account_moves = (
            moves.sudo().stock_valuation_layer_ids.account_move_id.filtered('id')
            | moves.account_move_id.filtered('id')
        )
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        if len(account_moves) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = account_moves.id
        else:
            action['domain'] = [('id', 'in', account_moves.ids)]
        return action

    def action_dn_view_svl(self):
        self.ensure_one()
        svl = self.move_ids.stock_valuation_layer_ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Valuation Layers'),
            'res_model': 'stock.valuation.layer',
            'view_mode': 'list,form',
            'domain': [('id', 'in', svl.ids)],
        }
