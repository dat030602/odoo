# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class BankStatementPartnerLine(models.Model):
    _name = 'bank.statement.partner.line'
    _description = 'Sổ Phụ Ngân Hàng'

    name = fields.Char()
    amount = fields.Monetary(string='Số tiền', tracking=True, required=True)
    sale_amount = fields.Monetary(string='Số tiền đơn hàng', compute='_compute_sale_amount', store=True)
    diff_amount = fields.Monetary(string='Chênh lệch', compute='_compute_diff_amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)

    partner_id = fields.Many2one('res.partner', string='Khách hàng', required=True)
    sale_ids = fields.Many2many('sale.order', string='Đơn hàng', domain="[('partner_id', '=', partner_id)]", required=True)
    parent_id = fields.Many2one('bank.statement.line', string='Sổ phụ')
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

    @api.depends('sale_ids', 'sale_ids.amount_total')
    def _compute_sale_amount(self):
        for rec in self:
            rec.sale_amount = sum(rec.sale_ids.mapped('amount_total'))

    @api.depends('amount', 'sale_amount')
    def _compute_diff_amount(self):
        for rec in self:
            rec.diff_amount = rec.amount - rec.sale_amount
