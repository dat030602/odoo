from odoo import models, fields, api, _

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    is_remanufacturing_order = fields.Boolean(string="Is Remanufacturing Order", default=False)
