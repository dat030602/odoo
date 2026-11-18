# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MisaEinvoiceDocumentLine(models.Model):
    _name = 'misa.einvoice.document.line'
    _description = 'MISA e-Invoice Detail Line (OriginalInvoiceDetail)'
    _order = 'line_number asc, id asc'

    document_id = fields.Many2one(
        'misa.einvoice.document',
        string='e-Invoice Document',
        required=True,
        ondelete='cascade',
        index=True
    )
    line_number = fields.Integer(string='Line No.', default=1)
    sort_order = fields.Integer(string='Sort Order', default=1, help='Sequential order starting from 1 (NULL for discount/note)')

    item_type = fields.Selection([
        ('1', 'Standard Goods / Service (Hang hoa/dich vu)'),
        ('2', 'Promotional Item (Khuyen mai)'),
        ('3', 'Commercial Discount (Chiet khau thuong mai)'),
        ('4', 'Note / Description (Ghi chu/dien giai)'),
        ('5', 'Vehicle / Transportation (Van tai/kinh doanh xe)'),
    ], string='Item Type', required=True, default='1')

    item_code = fields.Char(string='Item Code')
    item_name = fields.Char(string='Item Name', required=True)
    unit_name = fields.Char(string='Unit of Measure')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    unit_price = fields.Float(string='Unit Price', digits='Product Price', default=0.0)

    amount_oc = fields.Monetary(string='Amount (OC)', currency_field='currency_id')
    amount = fields.Monetary(string='Amount', currency_field='company_currency_id')

    discount_rate = fields.Float(string='Discount Rate (%)', digits='Discount', default=0.0)
    discount_amount_oc = fields.Monetary(string='Discount (OC)', currency_field='currency_id')
    discount_amount = fields.Monetary(string='Discount', currency_field='company_currency_id')

    amount_without_vat_oc = fields.Monetary(string='Amount Without VAT (OC)', currency_field='currency_id')
    amount_without_vat = fields.Monetary(string='Amount Without VAT', currency_field='company_currency_id')

    vat_rate_name = fields.Char(string='VAT Rate', default='10%')
    vat_amount_oc = fields.Monetary(string='VAT Amount (OC)', currency_field='currency_id')
    vat_amount = fields.Monetary(string='VAT Amount', currency_field='company_currency_id')

    # Automobile / Vehicle Tracking (ItemType = 5)
    chassis_number = fields.Char(string='Chassis Number (Số khung)')
    engine_number = fields.Char(string='Engine Number (Số máy)')
    license_plate = fields.Char(string='License Plate (Biển kiểm soát)')

    # Lot & Expiry tracking
    lot_no = fields.Char(string='Lot / Serial Number')
    expiry_date = fields.Date(string='Expiry Date')

    currency_id = fields.Many2one(related='document_id.currency_id', string='Currency', readonly=True)
    company_currency_id = fields.Many2one(related='document_id.company_id.currency_id', string='Company Currency', readonly=True)

    @api.onchange('quantity', 'unit_price', 'discount_rate', 'vat_rate_name')
    def _onchange_line_amounts(self):
        for line in self:
            cur = line.currency_id or line.env.company.currency_id
            comp_cur = line.company_currency_id or line.env.company.currency_id
            rate = line.document_id.exchange_rate or 1.0

            # Calculate amount_oc
            raw_amount_oc = line.quantity * line.unit_price
            line.amount_oc = cur.round(raw_amount_oc)
            line.amount = comp_cur.round(line.amount_oc * rate)

            # Discount
            if line.discount_rate:
                raw_disc_oc = line.amount_oc * (line.discount_rate / 100.0)
                line.discount_amount_oc = cur.round(raw_disc_oc)
                line.discount_amount = comp_cur.round(line.discount_amount_oc * rate)
            else:
                line.discount_amount_oc = 0.0
                line.discount_amount = 0.0

            # Amount without VAT
            line.amount_without_vat_oc = line.amount_oc - line.discount_amount_oc
            line.amount_without_vat = comp_cur.round(line.amount_without_vat_oc * rate)

            # VAT rate parsing
            vat_pct = 0.0
            if line.vat_rate_name:
                cleaned = line.vat_rate_name.replace('%', '').strip()
                try:
                    vat_pct = float(cleaned)
                except ValueError:
                    vat_pct = 0.0

            raw_vat_oc = line.amount_without_vat_oc * (vat_pct / 100.0)
            line.vat_amount_oc = cur.round(raw_vat_oc)
            line.vat_amount = comp_cur.round(line.vat_amount_oc * rate)
