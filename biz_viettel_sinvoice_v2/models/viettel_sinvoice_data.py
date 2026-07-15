# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api
import logging
from .viettel_sinvoice_item_type_set import ITEM_TYPE_SELECTION
_logger = logging.getLogger(__name__)
from odoo.addons import decimal_precision as dp

class ViettelSinvoiceData(models.Model):
    _name = "viettel.sinvoice.data"
    _description = "Invoice Data for S-Invoice issuance"

    @api.model
    def _default_vsi_item_type(self):
        if self._context.get('default_display_type') in ('line_note', 'line_section'):
            return 'ghi_chu'
        return 'hang_hoa'
    
    
    @api.depends('price_unit', 'discount', 'tax_ids', 'quantity',
        'product_id', 'sinvoice_id.partner_vat_id', 'sinvoice_id.currency_id', 'sinvoice_id.company_id',
        'sinvoice_id.date_invoice', 'sinvoice_id.date')
    def _compute_price(self):
        for res in self:
            currency = res.sinvoice_id and res.sinvoice_id.currency_id or None
            price = res.price_unit * (1 - (res.discount or 0.0) / 100.0)
            taxes = False
            if res.tax_ids:
                taxes = res.tax_ids.compute_all(price_unit=price, currency=currency, quantity=res.quantity, product=res.product_id, partner=res.sinvoice_id.partner_vat_id)
            res.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else res.quantity * price
            res.price_total = taxes['total_included'] if taxes else res.price_subtotal
            if res.sinvoice_id.currency_id and res.sinvoice_id.currency_id != res.sinvoice_id.company_id.currency_id:
                currency = res.sinvoice_id.currency_id
                date = res.sinvoice_id.date
                price_subtotal_signed = currency._convert(price_subtotal_signed, res.sinvoice_id.company_id.currency_id, res.company_id or res.env.user.company_id, date or fields.Date.today())
            sign = res.sinvoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
            res.price_subtotal_signed = price_subtotal_signed * sign

    @api.model
    def _default_account(self):
        if self._context.get('company_id'):
            company = self.env['res.company'].browse(self._context.get('company_id'))
        if self._context.get('journal_id'):
            journal = self.env['account.journal'].browse(self._context.get('journal_id'))
            if self._context.get('type') in ('out_invoice', 'in_refund'):
                if journal:
                    return journal.default_account_id.id
                elif company:
                    return company.account_journal_payment_credit_account_id.id
            if journal:
                return journal.default_account_id.id
            elif company:
                return company.account_journal_payment_debit_account_id.id

    def _get_price_tax(self):
        for l in self:
            l.price_tax = l.price_total - l.price_subtotal

    name = fields.Text(string='Description', required=True)
    origin = fields.Char(string='Source Document', help="Reference of the document that produced this invoice.")
    sequence = fields.Integer(default=10, help="Gives the sequence of this line when displaying the invoice.")
    
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', ondelete='set null', index=True)
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', index=True)
    account_id = fields.Many2one('account.account', string='Account', domain=[('deprecated', '=', False)], default=_default_account, help="The income or expense account related to the selected product.")
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price')
    price_subtotal = fields.Monetary(string='Amount (without Taxes)', store=True, readonly=True, compute='_compute_price', help="Total amount without taxes")
    price_total = fields.Monetary(string='Amount (with Taxes)', store=True, readonly=True, compute='_compute_price', help="Total amount with taxes")
    price_subtotal_signed = fields.Monetary(string='Amount Signed', currency_field='company_currency_id', store=True, readonly=True, compute='_compute_price',
        help="Total amount in the currency of the company, negative for credit note.")
    price_tax = fields.Monetary(string='Tax Amount', compute='_get_price_tax', store=False)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1)
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    tax_ids = fields.Many2many('account.tax', 'account_invoice_data_tax', 'invoice_data_id', 'tax_id',
        string='Taxes', domain=[('type_tax_use','!=','none'), '|', ('active', '=', False), ('active', '=', True)])
    
    edit_type = fields.Selection([
            ('increase', 'Increase'),
            ('reduction', 'Reduction quantity'),
            ('reduction_price','Reduction price')
        ], string='Edit Type')
    model = fields.Char(string="Model")
    reference_id = fields.Char(string="Reference")
    
    company_id = fields.Many2one('res.company', string='Company', related='sinvoice_id.company_id', store=True, readonly=True, related_sudo=False)
    partner_vat_id = fields.Many2one('res.partner', string='Partner', related='sinvoice_id.partner_vat_id', store=True, readonly=True, related_sudo=False)
    currency_id = fields.Many2one('res.currency', related='sinvoice_id.currency_id', store=True, related_sudo=False, readonly=False)
    company_currency_id = fields.Many2one('res.currency', related='sinvoice_id.company_currency_id', readonly=True, related_sudo=False)
    invoice_type = fields.Selection(related='sinvoice_id.type', readonly=True)
    sinvoice_id = fields.Many2one('viettel.sinvoice', string='Sinvoice', ondelete='cascade', index=True)
    display_type = fields.Selection([
		('line_section', "Section"),
		('line_note', "Note")], default=False)
    vsi_item_type = fields.Selection(ITEM_TYPE_SELECTION, string='Loại mặt hàng', default=_default_vsi_item_type)
    sequence = fields.Integer(string="Sequence")
    
    @api.onchange('product_id')
    def change_id_product(self):
        self.name = self.product_id and self.product_id.name or ''
        if self.product_id:
            detailed_type = getattr(self.product_id, 'detailed_type', False) or getattr(self.product_id, 'type', False)
            if detailed_type in ['product', 'consu', 'service']:
                self.vsi_item_type = 'hang_hoa'

    @api.onchange('display_type')
    def onchange_display_type(self):
        if self.display_type in ('line_note', 'line_section'):
            self.vsi_item_type = 'ghi_chu'
