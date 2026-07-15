from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order.line"

    move_amount_paid = fields.Monetary(string="Số tiền đã thanh toán", compute='_compute_amount_reconcile')
    move_amount_residual = fields.Monetary(string="Số tiền chưa thanh toán", compute='_compute_amount_reconcile')
    move_amount_invoiced = fields.Monetary(string="Số tiền xuất hóa đơn", compute='_compute_amount_reconcile')
    move_invoice_status = fields.Selection(string="Trạng thái xuất hóa đơn", selection=[
        ('no','Chưa lập hóa đơn'),
        ('to_invoice','Đã xuất hóa đơn'),
        ('invoiced','Đã xuất hóa đơn đầy đủ'),
    ], compute='_compute_move_invoice_status', store=True)

    payment_state = fields.Selection(string="Trạng thái thanh toán", selection=[
        ('not_paid', 'Chưa thanh toán'),
        ('partial', 'Thanh toán một phần'),
        ('in_payment', 'Thanh toán'),
        ('paid', 'Đã thanh toán'),
    ], compute='_compute_payment_state', store=True)

    @api.depends('qty_invoiced')
    def _compute_move_invoice_status(self):
        for rec in self:
            quantity = sum(rec.mapped('qty_invoiced'))
            status = 'no'
            if quantity >= rec.product_uom_qty:
                status = 'invoiced'
            elif quantity < rec.product_uom_qty and quantity > 0:
                status = 'to_invoice'
            rec.move_invoice_status = status

    @api.depends('invoice_lines.move_id.payment_state')
    def _compute_payment_state(self):
        for rec in self:
            invoice_lines = rec.invoice_lines.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund') and r.parent_state in ['posted','draft'])
            move_ids = invoice_lines.mapped('move_id')

            invoice_lines = invoice_lines.filtered(lambda r:r.parent_state == 'posted')
            if rec.is_promotional_product or rec.product_uom_qty == 0:
                rec.payment_state = 'paid'
                continue
            elif not move_ids:
                rec.payment_state = 'not_paid'
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

    def _compute_amount_reconcile(self):
        for rec in self:
            invoice_lines = rec.invoice_lines.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund') and r.parent_state in ['posted','draft'])
            amount_residual = 0
            amount_total = 0
            domain = [('account_type', 'in', ('asset_receivable', 'liability_payable')),]
            move_ids = invoice_lines.mapped('move_id')
            for move_id in move_ids:
                receivable_liability_payable_line = move_id.line_ids.filtered_domain(domain)
                reconciled = receivable_liability_payable_line.reconciled
                total_amount_balance = abs(receivable_liability_payable_line.balance)
                total_amount_residual = abs(receivable_liability_payable_line.balance)
                amount_paid = (total_amount_balance - total_amount_residual) / (len(move_id.invoice_line_ids) or 1)
                for line in invoice_lines.filtered(lambda l:l.move_id == move_id):
                    if not reconciled:
                        amount_residual += abs(line.price_total) - amount_paid
                    amount_total += abs(line.price_total)
            rec.move_amount_residual = amount_residual
            rec.move_amount_invoiced = amount_total
            rec.move_amount_paid = amount_total - amount_residual
