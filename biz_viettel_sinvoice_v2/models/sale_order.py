# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    vat_invoice_number = fields.Char(string="VAT Invoice Number", compute="_compute_vat_invoice_number")

    @api.depends('invoice_ids')
    def _compute_vat_invoice_number(self):
        for record in self:
            if record.invoice_ids:
                name_list = [invoice.vat_sinvoice_number for invoice in record.invoice_ids.filtered(lambda x: x.vat_sinvoice_number)]
                record.vat_invoice_number = ', '.join([name for name in name_list])
            else:
                record.vat_invoice_number = False
                
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    def _prepare_invoice_line(self, **optional_values):
        
        res = super()._prepare_invoice_line()
        res['name'] = self.product_id.name or self.name
        return res
