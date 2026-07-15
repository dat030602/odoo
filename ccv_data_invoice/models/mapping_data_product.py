from odoo import models, fields, api

class MappingDataProduct(models.Model):
    _name = 'mapping.data.product'
    _description = 'Mapping sản phẩm từ dữ liệu hóa đơn'
    _rec_name = 'keyword'

    keyword = fields.Char(
        string='Từ khóa mapping',
        required=True,
        help='Từ khóa để tìm kiếm và mapping sản phẩm từ dữ liệu hóa đơn'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        help='Sản phẩm được mapping với từ khóa'
    )
    
    active = fields.Boolean(
        string='Hoạt động',
        default=True
    )

    create_auto = fields.Boolean(
        string='Tạo tự động',
        default=False
    )
    
    note = fields.Text(
        string='Ghi chú'
    )

    account_id = fields.Many2one(
        'account.account',
        string='Tài khoản',
        help='Tài khoản được mapping với từ khóa'
    )


    @api.model
    def search_product_by_keyword(self, keyword):
        """Tìm sản phẩm dựa trên từ khóa"""
        mapping = self.search([('keyword', 'ilike', keyword)], limit=1)
        if mapping:
            return mapping.product_id
        return self.env['product.product']
