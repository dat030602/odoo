from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    is_gift_product = fields.Boolean(string="Hàng tặng", default=False)

