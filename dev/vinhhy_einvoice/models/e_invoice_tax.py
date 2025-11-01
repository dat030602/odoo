# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.tools.float_utils import float_round as round


class EInvoiceTax(models.Model):
    _name = 'einvoice.tax'
    _description = 'E-Invoice Tax'

    name = fields.Char(string='Name', required=True)
    amount = fields.Float(string='Amount', default=0.0, digits=(16, 4))

    def _compute_amount_tax(self, base_amount):
        return base_amount * self.amount / 100

    def compute_amount_all(self, price_unit, quantity=1.0, currency=None):
        company = self.env.company
        if not currency:
            currency = company.currency_id
        prec = currency.rounding

        base = currency.round(price_unit * quantity)
        tax_amount = round(self._compute_amount_tax(base), precision_rounding=prec)
        total = round(base + tax_amount, precision_rounding=prec)
        return {
            'tax_amount': tax_amount,
            'total_excluded': base,
            'total_included': total,
        }
