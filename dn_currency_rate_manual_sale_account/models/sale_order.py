from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.rate_mode == 'custom':
            invoice_vals.update({
                'rate_mode': 'custom',
                'selected_rate_id': self.selected_rate_id.id,
            })
        return invoice_vals
