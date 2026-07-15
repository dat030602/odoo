# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_order_type_id = fields.Many2one(comodel_name='purchase.order.type', string='Purchase Order Type ID', copy=False, domain="[('company_id', '=', company_id)]")

    @api.constrains('purchase_order_type_id')
    def check_sale_order_type_id(self):
        for record in self:
            if record.purchase_order_type_id and record.company_id:
                if record.purchase_order_type_id.company_id != record.company_id:
                    raise ValidationError(_("Current purchase order type belongs to the company %s. Please choose another purchase order type", record.purchase_order_type_id.company_id.name))

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    amount_conversion = fields.Float('Amount Conversion', readonly=True)
    conversion_unit = fields.Many2one('uom.uom', string='Conversion Unit')



    @api.onchange('product_uom_qty', 'conversion_unit','product_uom')
    def _onchange_amount_conversion(self):
        uom = self.product_uom
        conversion_uom = self.conversion_unit
        if uom.name == conversion_uom.name:
            self.amount_conversion = self.product_qty
        elif conversion_uom.uom_type == 'reference':
            if uom.uom_type == 'smaller':
                self.amount_conversion = self.product_uom_qty * uom.factor
            else:
                self.amount_conversion = self.product_uom_qty / conversion_uom.factor
        elif conversion_uom.uom_type == 'smaller':
            if uom.uom_type == 'reference':
                self.amount_conversion = self.product_uom_qty * conversion_uom.factor
            else:
                self.amount_conversion = (self.product_uom_qty / uom.factor) * conversion_uom.factor
        elif conversion_uom.uom_type == 'bigger':
            if uom.uom_type == 'reference':
                self.amount_conversion = conversion_uom.factor / self.product_uom_qty
            else:
                self.amount_conversion = ((self.product_uom_qty * uom.factor)/conversion_uom.factor)

