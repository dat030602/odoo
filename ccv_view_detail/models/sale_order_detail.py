from odoo import models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_view_detail_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết đơn bán hàng',
            'res_model': 'sale.order.detail.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        } 