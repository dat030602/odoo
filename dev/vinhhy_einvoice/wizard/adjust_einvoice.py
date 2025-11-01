# -*- coding: utf-8 -*-
from odoo import models, fields, api

ADJUSTMENT_INVOICE_TYPE = [
    ('1', 'Replacement Invoice'),
    ('2', 'Adjust increase'),
    ('3', 'Adjust decrease'),
    ('4', 'Adjust information')
]

class AdjustEInvoice(models.TransientModel):
    _name = 'adjust.einvoice'
    _description = 'Adjust E-Invoice'

    adjustmentInvoiceType = fields.Selection(ADJUSTMENT_INVOICE_TYPE, string='Adjustment Invoice Type', default=False)
    seller_responsible = fields.Many2one('res.users')
    seller_position = fields.Char(string='Seller Position')
    seller_address = fields.Char(string='Seller Address')
    buyer_responsible = fields.Many2one('res.partner')
    buyer_position = fields.Char(string='Buyer Position')
    buyer_address = fields.Char(string='Buyer Address')
    vh_einv_id = fields.Many2one('vinhhy.einvoice', string='Vinh Hy E-Invoice')

    @api.model
    def default_get(self, fields):
        res = super(AdjustEInvoice, self).default_get(fields)
        active_id = self._context.get('active_id')
        res.update({'vh_einv_id': active_id})
        return res

    def _prepare_vh_einv_line_values(self):
        line_vals = []
        for line in self.vh_einv_id.line_ids:
            val = (0, 0, {
                'name': line.name,
                'account_id': line.account_id.id,
                'price_unit': line.price_unit,
                'quantity': 1,
                'discount': 0,
                'uom_id': line.uom_id.id,
                'product_id': line.product_id.id,
                'vat_product_id': line.vat_product_id.id,
                'vh_inv_line_tax_id': line.vh_inv_line_tax_id.id,
                'base_einv_line_id': line.id,
            })
            line_vals.append(val)
        return line_vals

    def action_create_adjust_inv(self):
        action = self.env["ir.actions.actions"]._for_xml_id("vinhhy_einvoice_service.action_vinhhy_einvoice")
        action['views'] = [(self.env.ref('vinhhy_einvoice_service.vinhhy_einvoice_form').id, 'form')]
        action['target'] = 'current'
        vh_einv_line_vals = self._prepare_vh_einv_line_values()
        action['context'] = {
            'default_invoice_ids': self.vh_einv_id.invoice_ids.ids,
            'default_partner_id': self.vh_einv_id.partner_id.id,
            'default_partner_vat_id': self.vh_einv_id.partner_vat_id.id,
            'default_customer_name': self.vh_einv_id.customer_name,
            'default_legal_customer_name': self.vh_einv_id.legal_customer_name,
            'default_customer_vat': self.vh_einv_id.customer_vat,
            'default_customer_address': self.vh_einv_id.customer_address,
            'default_customer_email': self.vh_einv_id.customer_email,
            'default_is_individual_customer': self.vh_einv_id.is_individual_customer,
            'default_payment_method': self.vh_einv_id.payment_method,
            'default_vh_inv_tax_id': self.vh_einv_id.vh_inv_tax_id.id,
            'default_date_invoice': self.vh_einv_id.date_invoice,
            'default_line_ids': vh_einv_line_vals,
            'default_vh_inv_template_id': self.vh_einv_id.vh_inv_template_id.id,
            'default_einv_type': 'replacement_invoice' if self.adjustmentInvoiceType == '1' else 'adjustment_invoice', #là loại hóa đơn điều chỉnh/thay thế 
            'default_adjustmentInvoiceType': self.adjustmentInvoiceType,
            'default_base_ei_id': self.vh_einv_id.id,
            'default_seller_responsible': self.seller_responsible.id,
            'default_seller_position': self.seller_position,
            'default_seller_address': self.seller_address,
            'default_buyer_responsible': self.buyer_responsible.id,
            'default_buyer_position': self.buyer_position,
            'default_buyer_address': self.buyer_address,
        }
        return action
