# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockWarehouse(models.Model):
	_inherit = 'stock.warehouse'

	priority = fields.Integer("Priority")