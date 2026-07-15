from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = 'product.template'

    unload_container_ids = fields.Many2many(
        'product.template',
        'product_unload_container_rel',
        'product_id',
        'container_id',
        string="Cảng hạ",
        domain="[('detailed_type','=','service')]"
    )
