# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleOrderType(models.Model):
    _name = "sale.order.type"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Sale Order Type"
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'The code of the sale must be unique !')
    ]

    name = fields.Char(string="Name Of Sale Type", translate=True, copy=False, tracking=True)
    code = fields.Char(string="Code Of Sale Type", copy=False, tracking=True)
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
