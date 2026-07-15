# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools
from odoo.tools import float_compare, float_is_zero

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    value_import = fields.Float('Value import',copy=False)
    unit_cost_float = fields.Float('Unit Cost Float')

    def action_update_value(self):
        # cr = self.env.cr
        for res in self:
            # for move_line in res.stock_move_id:
            #     cr.execute("""
            #         UPDATE stock_move
            #         SET quantity_done = %s
            #         WHERE id = %s
            # #     """, (abs(res.quantity), move_line.id))
            # for move_line in res.stock_move_id.move_line_ids:
            #     cr.execute("""
            #         UPDATE stock_move_line
            #         SET qty_done = %s
            #         WHERE id = %s
            #     """, (abs(res.quantity), move_line.id))
            value_update = res.value_import/res.quantity
            res.write({
                'value': res.value_import,
                'unit_cost': value_update,
                'unit_cost_float': value_update,
                'initial_value': res.value_import,
            })
            if res.account_move_id:
                for line in res.account_move_id.line_ids:
                    if line.credit:
                        line.with_context(check_move_validity=False).credit = abs(res.value_import)
                    if line.debit:
                        line.with_context(check_move_validity=False).debit = abs(res.value_import)

    def action_cancel_move(self):
        for res in self.filtered(lambda x: x.account_move_id):
            res.account_move_id.button_draft()
            res.account_move_id.button_cancel()

    def action_delete_layer(self):
        for res in self.sudo():
            if res.stock_move_id:
                res.stock_move_id.scrapped = True
                res.stock_move_id._action_cancel()
                res.stock_move_id.state = 'draft'
                res.stock_move_id.unlink()

            if res.account_move_id:
                res.account_move_id.button_draft()
                res.account_move_id.button_cancel()
                res.account_move_id.unlink()
            res.unlink()
