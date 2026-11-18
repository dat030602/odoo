# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MisaInbotDocumentLine(models.Model):
    _name = 'misa.inbot.document.line'
    _description = 'MISA INBOT Document Item Line'
    _order = 'line_number asc, id asc'

    document_id = fields.Many2one(
        'misa.inbot.document',
        string='INBOT Document',
        required=True,
        ondelete='cascade',
        index=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='document_id.company_id',
        store=True,
        index=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='document_id.currency_id',
        store=True
    )

    item_id = fields.Char(string='Item ID / Code', index=True)
    line_number = fields.Integer(string='Line Number', default=1)
    item_name = fields.Char(string='Item Name', required=True)
    unit_name = fields.Char(string='Unit of Measure')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    amount_without_vat = fields.Monetary(string='Amount Before Tax', currency_field='currency_id')

    vat_rate = fields.Selection([
        ('0', '0%'),
        ('5', '5%'),
        ('8', '8%'),
        ('10', '10%'),
        ('-1', 'Không chịu thuế (Non-taxable)'),
        ('-2', 'Không kê khai thuế (Tax exempt)'),
        ('-3', 'Khác (Other)'),
    ], string='VAT Rate', default='10')
    vat_amount = fields.Monetary(string='VAT Amount', currency_field='currency_id')
    discount_amount = fields.Monetary(string='Discount Amount', currency_field='currency_id')
    amount = fields.Monetary(string='Total Line Amount', currency_field='currency_id')

    kind = fields.Selection([
        ('0', 'Hàng hóa / Dịch vụ thường'),
        ('1', 'Khuyến mại'),
        ('2', 'Chiết khấu thương mại'),
        ('3', 'Ghi chú / Diễn giải'),
        ('4', 'Bảng kê'),
        ('5', 'Khác'),
    ], string='Item Kind', default='0')

    # Decree 70 Fields
    specific_product_type = fields.Selection([
        ('0', 'None'),
        ('1', 'Ô tô / Xe máy'),
        ('2', 'Bất động sản'),
        ('3', 'Khác'),
    ], string='Specific Product Type (Decree 70)', default='0')
    vehicle_frame_number = fields.Char(string='Vehicle Frame Number (Số khung)')
    vehicle_engine_number = fields.Char(string='Vehicle Engine Number (Số máy)')
    transport_license_plate = fields.Char(string='Transport License Plate')
    shipper_name = fields.Char(string='Shipper Name')
    shipper_address = fields.Char(string='Shipper Address')
    shipper_tax_code = fields.Char(string='Shipper Tax Code')
    shipper_identifier = fields.Char(string='Shipper Identifier (CCCD/Passport)')
