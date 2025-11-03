from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class TikTokProductMapping(models.Model):
    _name = 'tiktok.product.mapping'
    _description = 'TikTok Product Mapping'
    _rec_name = 'tiktok_product_name'

    tiktok_item_id = fields.Char(string='TikTok Item ID', required=True, index=True)
    tiktok_product_name = fields.Char(string='TikTok Product Name', required=True)
    tiktok_sku = fields.Char(string='SKU TikTok')
    odoo_product_id = fields.Many2one('product.product', string='Odoo Product', required=True)
    odoo_product_code = fields.Char(related='odoo_product_id.default_code', string='Odoo Product Code', store=True)
    active = fields.Boolean(string='Active', default=True)
    
    _sql_constraints = [
        ('tiktok_item_id_unique', 'unique(tiktok_item_id)', 'TikTok Item ID must be unique!'),
    ]

    @api.model
    def get_odoo_product(self, tiktok_item_id):
        """Get Odoo product from TikTok Item ID"""
        mapping = self.search([('tiktok_item_id', '=', tiktok_item_id), ('active', '=', True)], limit=1)
        if mapping:
            return mapping.odoo_product_id
        return None

    @api.model
    def create_mapping(self, tiktok_item_id, tiktok_product_name, tiktok_sku, odoo_product_id=False):
        """Create new mapping or update existing mapping"""
        existing = self.search([('tiktok_item_id', '=', tiktok_item_id)], limit=1)
        if existing:
            existing.write({
                'tiktok_product_name': tiktok_product_name,
                'tiktok_sku': tiktok_sku,
                'odoo_product_id': odoo_product_id,
                'active': True
            })
            return existing
        else:
            return self.create({
                'tiktok_item_id': tiktok_item_id,
                'tiktok_product_name': tiktok_product_name,
                'tiktok_sku': tiktok_sku,
                'odoo_product_id': odoo_product_id,
                'active': True
            })
