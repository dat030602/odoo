from odoo import models, fields,api

class ApprovalRentLine(models.Model):
    _name = 'approvals.rent.line'

    partner_id = fields.Many2one('res.partner', string="Khách hàng")
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    weight = fields.Float("Khối lượng (tấn)",digits='Stock Weight')
    amount = fields.Monetary("Cước phí (đơn giá)", currency_field='currency_id')
    total = fields.Monetary("Thành tiền", compute='_compute_total', store=True, currency_field='currency_id')
    transporter = fields.Char("Đơn vị vận chuyển")
    routes = fields.Char("Lộ trình")
    currency_id = fields.Many2one('res.currency', string="Đơn vị tiền tệ")
    approval_id = fields.Many2one('approval.request')

    @api.depends('weight', 'amount')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.weight * rec.amount

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['currency_id'] = self.env.user.company_id.currency_id.id
        return res
