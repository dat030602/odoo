# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountInvoiceLine(models.Model):
	_inherit = 'account.move.line'

	products_image = fields.Binary(string= "Product Image", compute='compute_new_image', help="Small-sized image of the product.")

	@api.onchange('product_id')
	def compute_new_image(self):
		for image_id in self:
			image_id.products_image = None
			for for_image in image_id.product_id:
				image_id.products_image = for_image.image_1920

class AccountInvoice(models.Model):
	_inherit = 'account.move'

	product_print = fields.Boolean(string= "Print Product Image")				