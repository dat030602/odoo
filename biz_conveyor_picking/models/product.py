# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,  _
import requests

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	product_length = fields.Float('Lenght (cm)')


class ProductProduct(models.Model):
	_inherit = 'product.product'

	product_length = fields.Float('Lenght (cm)')
