from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_generate_vietqr(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create VietQR Code'),
            'res_model': 'create.vietqr.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            },
        }
