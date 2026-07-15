# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    amount_conversion = fields.Float('Amount Conversion',readonly=True)
    conversion_unit = fields.Many2one('uom.uom', string='Conversion Unit')


    @api.onchange('inventory_quantity_auto_apply', 'conversion_unit', 'product_uom_id')
    def _onchange_amount_conversion(self):
        uom = self.product_uom_id
        conversion_uom = self.conversion_unit
        if uom.name == conversion_uom.name:
            self.amount_conversion = self.inventory_quantity_auto_apply
        elif conversion_uom.uom_type == 'reference':
            if uom.uom_type == 'smaller':
                self.amount_conversion = self.inventory_quantity_auto_apply * uom.factor
            else:
                self.amount_conversion = self.inventory_quantity_auto_apply / conversion_uom.factor
        elif conversion_uom.uom_type == 'smaller':
            if uom.uom_type == 'reference':
                self.amount_conversion = self.inventory_quantity_auto_apply * conversion_uom.factor
            else:
                self.amount_conversion = (self.inventory_quantity_auto_apply / uom.factor) * conversion_uom.factor
        elif conversion_uom.uom_type == 'bigger':
            if uom.uom_type == 'reference':
                self.amount_conversion = conversion_uom.factor / self.inventory_quantity_auto_apply
            else:
                self.amount_conversion = ((self.inventory_quantity_auto_apply * uom.factor) / conversion_uom.factor)
