from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PaymentRequest(models.Model):
    _inherit = 'payment.request'

    purchase_id = fields.Many2one('purchase.order', string='Đơn mua hàng')

    purchase_count = fields.Integer(compute='_compute_purchase_count')

    def _compute_purchase_count(self):
        for request in self:
            # Count the number of purchase orders linked to this payment request via the m2m field
            request.purchase_count = self.env['purchase.order'].search_count([
                ('payment_request_ids', 'in', request.id)
            ])

    def action_view_purchase_order(self):
        self.ensure_one()
        PurchaseOrder = self.env['purchase.order']
        purchases = PurchaseOrder.search([('payment_request_ids', 'in', self.id)])
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Đơn mua hàng'),
            'res_model': 'purchase.order',
            'domain': [('payment_request_ids', 'in', self.id)],
            'context': {'search_default_payment_request_ids': self.id},
        }
        if len(purchases) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': purchases.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
            })
        return action