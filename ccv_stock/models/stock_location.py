# -*- coding: utf-8 -*-

from odoo import models, fields, api

class StockLocation(models.Model):
	_inherit = 'stock.location'
	_order = 'sequence, complete_name, id'

	sequence = fields.Integer(string="Sequence", default=0)
