# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class BankDebitStatementPartnerLine(models.Model):
    _name = 'bank.debit.statement.partner.line'
    _description = 'Dòng Khách hàng Số dư nợ'

    name = fields.Char()
    amount = fields.Monetary(string='Số tiền', tracking=True, required=True)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)

    partner_id = fields.Many2one('res.partner', string='Khách hàng', required=True)
    sale_ids = fields.Many2many('sale.order', string='Đơn hàng', domain="[('partner_id', '=', partner_id)]", required=True)
    parent_id = fields.Many2one('bank.debit.statement.line', string='Số dư nợ ngân hàng')
    date = fields.Date(string='Ngày giao dịch', default=fields.Date.context_today, related='parent_id.date')

    @api.onchange('sale_ids')
    def _onchange_sale_ids(self):
        for rec in self:
            if rec.sale_ids.invoice_ids.filtered(lambda x: x.state == 'posted' and x.payment_state != 'paid'):
                cur_amount = rec.parent_id.amount - sum((rec.parent_id.line_ids - rec).mapped('amount'))
                cur_amount = cur_amount if cur_amount > 0 else 0
                amount_residual = sum(rec.sale_ids.invoice_ids.filtered(lambda x: x.state == 'posted' and x.payment_state != 'paid').mapped('amount_residual'))
                rec.amount = min(amount_residual, cur_amount)
            else:
                rec.amount = 0
