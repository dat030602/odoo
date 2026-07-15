# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PurchaseOrderType(models.Model):
    _name = 'purchase.order.type'
    _description = 'Purchase Order Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'The code of the purchase must be unique !')
    ]

    name = fields.Char(string="Name Of Purchase Order", translate=True, copy=False, tracking=True)
    code = fields.Char(string="Code Of Purchase Order", copy=False, tracking=True)
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)





