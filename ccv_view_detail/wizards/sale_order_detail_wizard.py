from odoo import models, fields

class SaleOrderDetailWizard(models.TransientModel):
    _name = 'sale.order.detail.wizard'
    _description = 'Wizard Chi tiết đơn bán hàng'

    order_id = fields.Many2one('sale.order', string='Đơn hàng', readonly=True)
    partner_id = fields.Many2one(related='order_id.partner_id', readonly=True)
    date_order = fields.Datetime(related='order_id.date_order', readonly=True)
    state = fields.Selection(related='order_id.state', readonly=True)
    order_line_ids = fields.One2many(related='order_id.order_line', readonly=True) 