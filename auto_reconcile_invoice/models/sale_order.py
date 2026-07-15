from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    move_amount_invoiced = fields.Monetary(string="Giá trị xuất hóa đơn", compute='_compute_payment_state')
    move_amount_payment = fields.Monetary(string="Số tiền phiếu thanh toán", compute='_compute_payment_state')
    move_invoice_status = fields.Selection(string="Trạng thái xuất hóa đơn", selection=[
        ('no','Chưa lập hóa đơn'),
        ('to_invoice','Đã xuất hóa đơn'),
        ('invoiced','Đã xuất hóa đơn đầy đủ'),
    ], compute='_compute_move_invoice_status', store=True)

    @api.depends('order_line.move_invoice_status')
    def _compute_move_invoice_status(self):
        for rec in self:
            lines = rec.order_line.mapped('move_invoice_status')
            status = 'no'
            if all(state == 'invoiced' for state in lines):
                status = 'invoiced'
            elif any(state in ['invoiced'] for state in lines) or any(state in ['to_invoice'] for state in lines):
                status = 'to_invoice'
            rec.move_invoice_status = status

    @api.depends('order_line.payment_state','order_line.move_amount_residual','order_line.move_amount_invoiced','order_line.move_amount_paid')
    def _compute_payment_state(self):
        for rec in self:
            rec.move_amount_residual = sum(rec.order_line.mapped('move_amount_residual'))
            rec.move_amount_invoiced = sum(rec.order_line.mapped('move_amount_invoiced'))
            payments = rec._get_payment()
            amount = 0
            for payment in payments:
                exchange_rate = 1
                if payment.apply_manual_currency_exchange and payment.inverse_manural_currency_exchange_rate:
                    exchange_rate = payment.inverse_manural_currency_exchange_rate
                size = len(payment.sale_ids)
                amount += payment.amount * exchange_rate / (size if size else 1)
            rec.move_amount_payment = amount
            if rec.invoice_count > 0:
                rec.move_amount_paid = sum(rec.order_line.mapped('move_amount_paid'))
            else:
                rec.move_amount_paid = amount
            payment_states = rec.order_line.filtered(lambda l: not l.is_promotional_product).mapped('payment_state')
            if all(state == 'paid' for state in payment_states):
                rec.payment_state = 'paid'
            elif any(state in ['paid'] for state in payment_states) or any(state in ['partial'] for state in payment_states):
                rec.payment_state = 'partial'
            elif any(state in ['in_payment'] for state in payment_states):
                rec.payment_state = 'in_payment'
            else:
                rec.payment_state = 'not_paid'

    def _get_payment(self):
        self.ensure_one()
        payments = self.env['account.payment'].sudo()
        payments = payments.search(['|',('sale_ids','in',[self.id]),('sale_id','in',[self.id])])
        return payments

    def action_open_vietqr_bank_transactions(self):
        amount = 0
        for order in self:
            invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            if invoices:
                amount += sum(invoices.mapped('amount_residual'))
            else:
                amount += order.amount_total
        tracsaction_id = self.env['vietqr.bank.transaction'].create({
            'name': 'Thanh toán đơn bán hàng %s' % ', '.join(self.mapped('name')),
            'sale_ids': [(6, 0, self.ids)],
            'amount': amount
        })
        tracsaction_id._onchange_code_ref()
        action = self.env.ref('auto_reconcile_invoice.action_vietqr_bank_transaction').sudo().read()[0]
        action['views'] = [(False, 'form')]
        action['res_id'] = tracsaction_id.id
        return action
