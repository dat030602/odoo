# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMoveSales(models.Model):
	_inherit = 'account.move'

	document_number_sale = fields.Char('Document Number')
	is_gift_entries = fields.Boolean('Bút toán quà tặng',copy=False)

	report_date = fields.Date(string='Report date', compute='_get_default_report_date', store=True,  readonly=False)

	@api.depends('invoice_date')				
	def _get_default_report_date(self):
		for rec in self:
			if rec.invoice_date:
				rec.report_date = rec.invoice_date

class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	product_not_taxable = fields.Boolean("HHDV is not taxable",compute="_compute_product_not_taxable",readonly=False,store=True)

	@api.depends('product_id')
	def _compute_product_not_taxable(self):
		for res in self:
			res.product_not_taxable = True if res.product_id.product_not_taxable else False


	
