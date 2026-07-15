from odoo import models, fields, api

class Uom(models.Model):
    _inherit = 'uom.uom'

    is_ton = fields.Boolean(string='Đơn vị Tấn')