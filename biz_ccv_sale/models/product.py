# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"

    packaging_image = fields.Image(string="Packaging Image", max_width=1024, max_height=1024, copy=False)


class ProductProduct(models.Model):
    _inherit = "product.product"

    packaging_image = fields.Image(string="Packaging Image", related="product_tmpl_id.packaging_image", max_width=1024, max_height=1024, copy=False, readonly=False)

