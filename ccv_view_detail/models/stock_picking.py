from odoo import models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_view_detail_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết phiếu kho',
            'res_model': 'stock.picking.detail.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id},
        } 
        