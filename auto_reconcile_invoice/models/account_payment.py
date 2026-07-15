from odoo import models, fields, api,_
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools import frozendict

import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    sale_ids = fields.Many2many("sale.order", string="Đơn bán hàng")
    purchase_ids = fields.Many2many("purchase.order", string="Đơn mua hàng")
    same_payment_id = fields.Many2one('account.payment', string="Thanh toán trùng", compute="_compute_same_payment_id")
    transaction_number = fields.Char(string="Số giao dịch", copy=False)
    
    @api.depends('sale_id','purchase_id', 'company_id', 'partner_id', 'date')
    def _compute_same_payment_id(self):
        for rec in self:
            if not rec.partner_id or not rec.date:
                rec.same_payment_id = False
                continue

            domain = [
                ('id', '!=', rec._origin.id),
                ('company_id', '=', rec.company_id.id),
                ('partner_id', '=', rec.partner_id.id),
                ('date', '=', rec.date),
                ('payment_type', '=', rec.payment_type),
            ]

            if rec.sale_id:
                domain += [('sale_id', '=', rec.sale_id.id)]
            elif rec.purchase_id:
                domain += [('purchase_id', '=', rec.purchase_id.id)]
            else:
                rec.same_payment_id = False
                continue

            rec.same_payment_id = rec.search(domain, limit=1)


    @api.onchange('sale_ids','purchase_ids','partner_id')
    def _onchange_order_diff_partner(self):
        """Kiểm tra đối tác của đơn hàng và thanh toán có khớp nhau không, nếu không thì báo lỗi."""
        for rec in self:
            if rec.payment_type == 'inbound':
                partner_ids = rec.sale_ids.mapped('partner_id')
            else:
                partner_ids = rec.purchase_ids.mapped('partner_id')
            if len(partner_ids) > 1:
                raise UserError('Một thanh toán không thể gắn với nhiều đối tác !!!')
            elif partner_ids and partner_ids != rec.partner_id:
                raise UserError('Đối tác đơn hàng và thành toán không giống nhau !!!')

    def _get_order_available(self):
        """Trả về danh sách các đơn bán hàng hoặc mua hàng gắn với thanh toán."""
        self.ensure_one()
        if self.payment_type == 'inbound':
            order_ids = self.env['sale.order']
            order_ids |= self.sale_ids
            order_ids |= self.sale_id
        else:
            order_ids = self.env['purchase.order']
            order_ids |= self.purchase_ids
            order_ids |= self.purchase_id
        return order_ids

    def _get_invoice_available(self):
        """Trả về danh sách các hóa đơn được tạo từ các đơn hàng liên quan."""
        self.ensure_one()
        order_ids = self._get_order_available()
        if not order_ids:
            return False
        move_ids = order_ids.mapped('order_line').mapped('invoice_lines').mapped('move_id')
        return move_ids

    def _get_invoice_line_available(self, payment_lines):
        """Trả về các dòng hóa đơn có thể đối soát với các dòng thanh toán."""
        self.ensure_one()
        move_ids = self._get_invoice_available()
        line_ids = self.env['account.move.line']
        if not move_ids:
            return False
        for move in move_ids:
            if move.state != 'posted' or move.payment_state not in ('not_paid', 'partial') or not move.is_invoice(include_receipts=True):
                continue
            pay_term_lines = move.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
            if self._can_reconcile(move, pay_term_lines, payment_lines):
                line_ids |= pay_term_lines
        return line_ids

    def _can_reconcile(self, move, pay_term_lines, payment_lines):
        """Kiểm tra hóa đơn có thể đối soát với dòng thanh toán không."""
        self.ensure_one()
        line_ids = self.env['account.move.line']
        domain = [
            ('account_id', 'in', pay_term_lines.account_id.ids),
            ('parent_state', '=', 'posted'),
            ('partner_id', '=', move.commercial_partner_id.id),
            ('reconciled', '=', False),
            '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
        ]

        if move.is_inbound():
            domain.append(('balance', '<', 0.0))
        else:
            domain.append(('balance', '>', 0.0))
        for line in self.env['account.move.line'].search(domain):
            if line.currency_id == move.currency_id:
                amount = abs(line.amount_residual_currency)
            else:
                amount = line.company_currency_id._convert(abs(line.amount_residual),move.currency_id,move.company_id,line.date,)
            if move.currency_id.is_zero(amount):
                continue
            line_ids |= line
        if line_ids and payment_lines in line_ids:
            return True
        return False

    def _reconcile_payments(self):
        """Thực hiện đối soát thanh toán với hóa đơn và gửi thông báo sau đối soát."""
        odoobot = self.env.ref('base.partner_root').sudo()
        for record in self:
            domain = [
                ('parent_state', '=', 'posted'),
                ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                ('reconciled', '=', False),
            ]
            payment_lines = record.line_ids.filtered_domain(domain)
            if not payment_lines:
                record.message_post(body=_('Đối soát thất bại: Không có dòng thanh toán để đối soát.'),message_type='comment',subtype_xmlid='mail.mt_note',author_id=odoobot.id)
                continue
            lines = record._get_invoice_line_available(payment_lines)
            if not lines:
                record.message_post(body=_('Đối soát thất bại: Không có dòng hóa đơn để đối soát.'),message_type='comment',subtype_xmlid='mail.mt_note',author_id=odoobot.id)
                continue

            # --- Thực hiện đối soát ---
            for account in payment_lines.account_id:
                matched_lines = (payment_lines + lines).filtered_domain([
                    ('account_id', '=', account.id),
                    ('reconciled', '=', False)
                ])
                if matched_lines:
                    res = matched_lines.reconcile()
                    for partial in res.get('partials'):
                        line_reconcile = partial.debit_move_id | partial.credit_move_id
                        payment_id = line_reconcile.mapped('payment_id')
                        amount = partial.amount
                        invoice_ids = line_reconcile.mapped('move_id').filtered(lambda move: move.is_invoice(include_receipts=True))
                        order_ids = invoice_ids.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
                        if invoice_ids.purchase_id:
                            order_ids = invoice_ids.purchase_id
                        message = 'Đã đối soát số tiền: {amount} cho {order}.'
                        msg = message.format(amount=self.currency_id.format(abs(amount)), order='Hóa đơn: %s' % invoice_ids._get_html_link())
                        for order in order_ids:
                            msg = message.format(amount=self.currency_id.format(abs(amount)), order='Đơn hàng: %s' % order._get_html_link())
                            payment_id.message_post(body=msg,message_type='comment',subtype_xmlid='mail.mt_note',author_id=odoobot.id)

                            msg = message.format(amount=self.currency_id.format(abs(amount)), order='Thanh toán: %s' % payment_id._get_html_link())
                            order.message_post(body=msg,message_type='comment',subtype_xmlid='mail.mt_note',author_id=odoobot.id)

            record.message_post(body=_('Đã đối soát thành công.'),message_type='comment',subtype_xmlid='mail.mt_note',author_id=odoobot.id)


    def reconcile_payments(self):
        for record in self.filtered(lambda l:l.state == 'posted'):
            record._reconcile_payments()

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        self.reconcile_payments()
        return res

    def write(self, vals):
        res = super(AccountPayment, self).write(vals)
        if 'sale_ids' in vals or 'purchase_ids' in vals:
            for rec in self.filtered(lambda p: p.state == 'posted'):
                rec.reconcile_payments()
        return res
