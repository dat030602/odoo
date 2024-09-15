from odoo import _, fields, api, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    commercial_entity = fields.Selection(selection=[('individual', 'Individual'), ('company', 'Company'), ('other', 'Other')], default="individual", store=True)