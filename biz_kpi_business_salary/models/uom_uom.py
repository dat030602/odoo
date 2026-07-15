from odoo import models, fields, api

class UomCommissionPrice(models.Model):
    """Extend uom.uom to add commission price field"""
    _inherit = 'uom.uom'

    commission_price = fields.Monetary(
        string='Đơn giá hoa hồng',
        help='Đơn giá hoa hồng cho đơn vị tính này'
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string='Loại tiền tệ', 
        default=lambda self: self.env.company.currency_id
    )
