# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MisaEinvoiceTaxLine(models.Model):
    _name = 'misa.einvoice.tax.line'
    _description = 'MISA e-Invoice Tax Rate Summary Line (TaxRateInfo)'
    _order = 'vat_rate_name asc, id asc'

    document_id = fields.Many2one(
        'misa.einvoice.document',
        string='e-Invoice Document',
        required=True,
        ondelete='cascade',
        index=True
    )
    vat_rate_name = fields.Char(string='VAT Rate Name', required=True, default='10%')
    amount_without_vat_oc = fields.Monetary(string='Amount Without VAT (OC)', currency_field='currency_id')
    amount_without_vat = fields.Monetary(string='Amount Without VAT', currency_field='company_currency_id')
    vat_amount_oc = fields.Monetary(string='VAT Amount (OC)', currency_field='currency_id')
    vat_amount = fields.Monetary(string='VAT Amount', currency_field='company_currency_id')

    currency_id = fields.Many2one(related='document_id.currency_id', string='Currency', readonly=True)
    company_currency_id = fields.Many2one(related='document_id.company_id.currency_id', string='Company Currency', readonly=True)
