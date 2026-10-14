from odoo import models, fields, api

class PackingListInheritProductTemplate(models.Model):
    _inherit = 'product.template'

    carton_ids = fields.One2many(comodel_name='carton.type', string='Packing List',inverse_name="product_id")