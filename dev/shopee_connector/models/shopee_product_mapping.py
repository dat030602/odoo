from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ShopeeProductMapping(models.Model):
    _name = 'shopee.product.mapping'
    _description = 'Shopee Product Mapping'
    _rec_name = 'shopee_product_name'

    shopee_item_id = fields.Char(string='Shopee Item ID', required=True, index=True)
    shopee_product_name = fields.Char(string='Shopee Product Name', required=True)
    shopee_sku = fields.Char(string='SKU Shopee')
    odoo_product_id = fields.Many2one('product.product', string='Odoo Product', required=True)
    odoo_product_code = fields.Char(related='odoo_product_id.default_code', string='Odoo Product Code', store=True)
    active = fields.Boolean(string='Active', default=True)
    
    _sql_constraints = [
        ('shopee_item_id_unique', 'unique(shopee_item_id)', 'Shopee Item ID must be unique!'),
    ]

    @api.model
    def get_odoo_product(self, shopee_item_id):
        """Get Odoo product from Shopee Item ID"""
        mapping = self.search([('shopee_item_id', '=', shopee_item_id), ('active', '=', True)], limit=1)
        if mapping:
            return mapping.odoo_product_id
        return None

    @api.model
    def create_mapping(self, shopee_item_id, shopee_product_name, shopee_sku, odoo_product_id=False):
        """Create new mapping or update existing mapping"""
        existing = self.search([('shopee_item_id', '=', shopee_item_id)], limit=1)
        if existing:
            existing.write({
                'shopee_product_name': shopee_product_name,
                'shopee_sku': shopee_sku,
                'odoo_product_id': odoo_product_id,
                'active': True
            })
            return existing
        else:
            return self.create({
                'shopee_item_id': shopee_item_id,
                'shopee_product_name': shopee_product_name,
                'shopee_sku': shopee_sku,
                'odoo_product_id': odoo_product_id,
                'active': True
            })
