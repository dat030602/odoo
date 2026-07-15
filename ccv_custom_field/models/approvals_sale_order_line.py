from odoo import models, fields,api

class ApprovalSaleOrderLine(models.Model):
    _name = 'approvals.sale.order.line'

    order_id = fields.Many2one('sale.order', string="Đơn hàng")
    partner_id = fields.Many2one('res.partner', string="Khách hàng")
    quantity = fields.Float(string="Số lượng")
    credit = fields.Monetary(string="Công nợ", related="partner_id.credit")
    credit_limit = fields.Monetary(string="Hạn mức công nợ", related="order_id.credit_limit")
    credit_over = fields.Monetary(string="Vượt hạn mức")
    amount = fields.Monetary("Thành tiền")
    amount_paid = fields.Monetary("Số tiền đã thanh toán")
    amount_residual = fields.Monetary("Số tiền chưa thanh toán")
    
    currency_id = fields.Many2one('res.currency', string="Tiền tệ")
    approval_id = fields.Many2one('approval.request')
    note = fields.Char("Ghi chú")
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['currency_id'] = self.env.user.company_id.currency_id.id
        return res
    
    @api.depends('credit','amount_residual')
    def _compute_credit_over(self):
        for rec in self:
            rec.credit_over = rec.credit + rec.amount_residual

    @api.onchange('order_id')
    def _onchange_order_ids(self):
        for rec in self:
            if rec.order_id:
                rec.partner_id = rec.order_id.partner_id
                rec.quantity = sum(rec.order_id.order_line.filtered(lambda l: 'tấn' in l.product_uom.name.lower()).mapped('product_uom_qty'))
                rec.amount = rec.order_id.amount_total
                rec.amount_paid = rec.order_id.move_amount_paid
                rec.amount_residual = rec.order_id.move_amount_residual
