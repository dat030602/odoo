from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_generate_sepay_qr(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Sepay QR Code'),
            'res_model': 'create.sepay.qr.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            },
        }
