from odoo import models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_view_detail_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Chi tiết đơn mua hàng',
            'res_model': 'purchase.order.detail.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        } 