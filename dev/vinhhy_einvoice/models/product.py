# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo import exceptions


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    vat_product_variant_ids = fields.Many2many('vat.product.template', 'product_vat_product_template_rel', 'product_id', 'vat_product_id', 'VAT Product', compute='_compute_vat_product_ids')

    def _compute_vat_product_ids(self):
        for prod in self:
            prod.vat_product_variant_ids = prod.product_variant_ids.mapped('vat_product_ids')

class Product(models.Model):
    _inherit = 'product.product'

    vat_product_ids = fields.Many2many('vat.product.template', 'product_vat_product_rel', 'product_id', 'vat_product_id', 'VAT Product')

    def _get_vat_product_template(self):
        max_available_qty = self.vat_product_ids[0] if self.vat_product_ids else self.env['vat.product.template']
        for prod in self.vat_product_ids:
            if prod.qty_available > max_available_qty.qty_available:
                max_available_qty = prod
        return max_available_qty
    