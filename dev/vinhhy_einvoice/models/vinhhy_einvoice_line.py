# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class VinhHyEInvoiceLine(models.Model):
    _name = 'vinhhy.einvoice.line'
    _description = 'Vinh Hy E-Invoice Line'

    @api.depends('price_unit', 'discount', 'tax_id', 'quantity',
                 'product_id', 'vh_inv_id.currency_id',
                 'vh_inv_id.company_id')
    def _compute_price(self):
        for line in self:
            currency = line.vh_inv_id and line.vh_inv_id.currency_id
            price = (line.price_unit) * (1 - (line.discount or 0.0) / 100.0)
            tax = line.tax_id.compute_all(price, currency, line.quantity, line.product_id, line.vh_inv_id.partner_id)
            # Set Unit Price after discount
            line.update({
                'price_reduce': price,
                'price_discount': (line.price_unit - price) * line.quantity,
                'price_tax': tax.get('tax_amount', 0),
                'price_total': tax.get('total_included', 0),
                'price_subtotal': tax.get('total_excluded', 0),
                'price_subtotal_signed': tax.get('total_excluded', 0),
            })
            if currency and currency != line.vh_inv_id.company_id.currency_id:
                rate_date = line.vh_inv_id.date_invoice
                price_subtotal_signed = currency._convert(line.price_subtotal_signed,
                                                          line.vh_inv_id.company_id.currency_id,
                                                          line.company_id or self.env.user.company_id,
                                                          rate_date or fields.Date.today())
                line.price_subtotal_signed = price_subtotal_signed

    @api.model
    def _default_account(self):
        if self._context.get('journal_id'):
            journal = self.env['account.journal'].browse(self._context.get('journal_id'))
            return journal.default_account_id.id

    vh_inv_id = fields.Many2one('vinhhy.einvoice', string='Vinh Hy E-Invoice', ondelete='cascade', required=True, index=True, copy=False, readonly=True)
    name = fields.Text(string='Description', store=True)
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', index=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', ondelete='set null', index=True)
    tax_id = fields.Many2one('account.tax', string='Taxes')
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price')
    price_reduce = fields.Float(string='Price Reduce', required=True, digits='Price Reduce', compute='_compute_price')
    price_tax = fields.Monetary(string='Tax Amount', compute='_compute_price', store=True, currency_field='company_currency_id')
    price_subtotal = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_price', currency_field='company_currency_id', 
        help="Total amount without taxes")
    price_total = fields.Monetary(string='Amount (with Taxes)', store=True, readonly=True, compute='_compute_price', currency_field='company_currency_id', 
        help="Total amount with taxes")
    price_subtotal_signed = fields.Monetary(string='Amount Signed', currency_field='company_currency_id', store=True,
        readonly=True, compute='_compute_price', help="Total amount in the currency of the company, negative for credit note.")
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    price_discount = fields.Monetary(string='Price Discount', store=True, compute='_compute_price', currency_field='company_currency_id')
    account_id = fields.Many2one('account.account', string='Account', domain=[('deprecated', '=', False)], default=_default_account,
        help="The income or expense account related to the selected product.")
    company_currency_id = fields.Many2one('res.currency', related='vh_inv_id.company_currency_id', readonly=True)
    base_einv_line_id = fields.Many2one('vinhhy.einvoice.line', string='Base Vinh Hy E-Invoice Line')
    # inv_line_source_id = fields.Many2one('account.move.line', string='Odoo Invoice Line')
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    company_id = fields.Many2one('res.company', related='vh_inv_id.company_id', default=lambda self: self.env.company)
