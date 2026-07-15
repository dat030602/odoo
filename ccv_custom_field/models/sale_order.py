from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    move_amount_paid = fields.Monetary(string="Số tiền đã thanh toán", compute='_compute_payment_state', compute_sudo=True)
    move_amount_residual = fields.Monetary(string="Số tiền chưa thanh toán", compute='_compute_payment_state', compute_sudo=True)

    payment_state = fields.Selection(string="Trạng thái thanh toán", selection=[
        ('not_paid', 'Chưa thanh toán'),
        ('partial', 'Thanh toán một phần'),
        ('in_payment', 'Thanh toán'),
        ('paid', 'Đã thanh toán'),
    ], compute='_compute_payment_state', store=True, compute_sudo=True)

    @api.depends('order_line.invoice_lines.move_id.payment_state')
    def _compute_payment_state(self):
        for rec in self:
            move_ids = rec.order_line.invoice_lines.move_id.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund'))
            # payment_id = self.env['account.payment'].sudo().search([('sale_id','=',rec.id),('state','=','posted')])
            # move_ids += payment_id.mapped('move_id')
            if not move_ids:
                rec.payment_state = 'not_paid'
                rec.move_amount_paid = 0
                rec.move_amount_residual = rec.amount_total
                continue
            payment_states = move_ids.mapped('payment_state')
            if all(state == 'paid' for state in payment_states):
                rec.payment_state = 'paid'
            elif any(state in ['paid'] for state in payment_states) or any(state in ['partial'] for state in payment_states):
                rec.payment_state = 'partial'
            elif any(state in ['in_payment'] for state in payment_states):
                rec.payment_state = 'in_payment'
            else:
                rec.payment_state = 'not_paid'
            rec.move_amount_residual = sum(move_ids.mapped('amount_residual'))
            rec.move_amount_paid = rec.amount_total - rec.move_amount_residual
