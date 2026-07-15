# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleOderLine(models.Model):
	_inherit = 'sale.order.line'

	product_image = fields.Binary(string= "Product Image", compute='compute_get_image', help="Small-sized image of the product.", store=True)

	@api.depends('product_id')
	def compute_get_image(self):
		for record in self:
			product_image = None
			if record.product_id and record.product_id.image_1024:
				product_image = record.product_id.image_1024
			record.product_image = product_image


class SaleOrder(models.Model):
	_inherit = 'sale.order'

	product_print = fields.Boolean(string= "Print Product Image")
			