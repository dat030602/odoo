# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductProduct(models.Model):
	_inherit = 'product.product'
	
	def _prepare_in_svl_vals(self, quantity, unit_cost):
		value = super(ProductProduct,self)._prepare_in_svl_vals(quantity,unit_cost)
		if 'value_import' in self._context:
			value.update({
				'value': self._context.get('value_import'),
				'unit_cost': self._context.get('value_import')/quantity
			})
		return value
