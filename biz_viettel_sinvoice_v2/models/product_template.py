from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    description_vat = fields.Char('Description VAT')
