from odoo import api, fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    payment_count = fields.Integer(compute='_compute_payment_count')
    payment_request_ids = fields.Many2many(
        'payment.request',
        'purchase_order_payment_request_rel',
        'purchase_order_id',
        'payment_request_id',
        string='Đề nghị thanh toán'
    )

    def _compute_payment_count(self):
        for order in self:
            order.payment_count = self.env['payment.request'].search_count([('purchase_id', '=', order.id)])

    def action_open_payment_wizard(self):
        self.ensure_one()
        return {
            'name': 'Đề nghị thanh toán',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.payment.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
                'default_amount': self.amount_total,
                'default_currency_id': self.currency_id.id,
            }
        }

    def action_view_purchase_payments(self):
        self.ensure_one()
        PaymentRequest = self.env['payment.request']
        payments = PaymentRequest.search([('purchase_id', '=', self.id)])
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Đề nghị thanh toán',
            'res_model': 'payment.request',
            'domain': [('purchase_id', '=', self.id)],
            'context': {'search_default_purchase_id': self.id},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
            })
        return action
