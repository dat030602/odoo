from odoo import models, fields, api

class GdtMapProduct(models.Model):
    _name = 'gdt.map.product'
    _description = 'Product Mapping from Invoice Data'

    # ========== Basic Fields ==========
    keyword = fields.Char(
        string='Mapping Keyword',
        required=True,
        help='Keyword to search and map products from invoice data'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help='Product mapped to the keyword'
    )

    # ========== Status Fields ==========
    active = fields.Boolean(string='Active', default=True)
    create_auto = fields.Boolean(string='Auto Created', default=False)

    # ========== Helper Methods ==========
    @api.model
    def search_product_by_keyword(self, keyword):
        """Find product based on keyword"""
        mapping = self.search([('keyword', 'ilike', keyword)], limit=1)
        if mapping:
            return mapping.product_id
        return self.env['product.product']
