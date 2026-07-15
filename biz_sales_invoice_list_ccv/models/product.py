# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountAccountTag(models.Model):
	_inherit = 'product.template'

	product_not_taxable = fields.Boolean("HHDV is not taxable")
	product_general_vat = fields.Many2one("product.template", string="Sản phẩm chung VAT")
 
	