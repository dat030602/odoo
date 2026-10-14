# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import format_date, frozendict


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'
    
    x_is_packing_list = fields.Boolean(string="Is Packing List", default=False)
    x_invoice_service = fields.Boolean(string="Invoice The Services", default=False)
    x_deduct_downpayments = fields.Boolean(string="Deduct Downpayments", default=False)

    def create_invoices(self):
        self = self.with_context(x_invoice_service=self.x_invoice_service,x_deduct_downpayments=self.x_deduct_downpayments)
        return super(SaleAdvancePaymentInv,self).create_invoices()