from odoo import models, api
from datetime import datetime, timedelta

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _set_backdate(self, backdate):
        """
        set backdate for done stock moves and their conresponding done stock move lines
        """

        self.filtered(lambda x: x.state == 'done').write({'date': backdate})
        move_line_ids = self.mapped('move_line_ids').filtered(lambda x: x.state == 'done')
        account_move_ids = self.mapped('account_move_ids').filtered(lambda x: x.state == 'posted')
        stock_valuation_layer_ids = self.sudo().mapped('stock_valuation_layer_ids')
        if self.picking_id:
            picking = self.env['stock.picking'].browse(self.picking_id.ids)
            if picking:
                picking.write({'date_done': backdate})
        if move_line_ids:
            move_line_ids.write({'date': backdate})
        if stock_valuation_layer_ids:
            for layer in stock_valuation_layer_ids:
                self.env.cr.execute("UPDATE stock_valuation_layer SET create_date=%s WHERE id=%s", (backdate, layer.id))
        if account_move_ids:
            backdate_account = (datetime.strptime(str(backdate), "%Y-%m-%d %H:%M:%S")) + timedelta(hours=7)
            account_move_ids.button_draft()
            account_move_ids.write({'date': backdate_account.date()})
            account_move_ids.action_post()

    def update_date_by_production_id(self):
        for rec in self:
            if rec.production_id:
                if rec.move_line_ids:
                    for move in rec.move_line_ids:
                        rec.date = move.date
