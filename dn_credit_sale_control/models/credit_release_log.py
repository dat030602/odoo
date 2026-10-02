from odoo import api, fields, models

class CreditReleaseLog(models.Model):
    _name = 'credit.release.log'
    _description = 'Credit Release Log'

    partner_id = fields.Many2one('res.partner')
    sale_order_id = fields.Many2one('sale.order')
    picking_id = fields.Many2one('stock.picking')
    release_type = fields.Selection([
        ('sale_order', 'Sale Order'),
        ('delivery', 'Delivery')
    ])
    exposure = fields.Float()
    limit = fields.Float()
    overdue_days = fields.Integer()
    reason = fields.Text()
    approved_by = fields.Many2one('res.users')
    date = fields.Datetime()
