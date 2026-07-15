# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMove(models.Model):
	_inherit = 'account.move'

	document_number = fields.Char('Document Number')
	document_date = fields.Date('Document Date')
	invoice_code = fields.Char('Invoice Code')
	
class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	product_shared = fields.Boolean("HHDV Shared",compute="_compute_product_shared",readonly=False,store=True)
	invoice_code = fields.Char('Invoice Template Code')
	invoice_number = fields.Char('Invoice Form/Number')
	date_invoice = fields.Date('Invoice Date')
	vat_invoice_number = fields.Char('Số hoá đơn VAT', related="move_id.vat_sinvoice_number", store=True)

	@api.depends('product_id')
	def _compute_product_shared(self):
		for res in self:
			res.product_shared = True if res.product_id.general_product else False

	@api.depends("invoice_code",'invoice_number','date_invoice')
	def _compute_all_tax(self):
		super(AccountMoveLine, self)._compute_all_tax()
		for line in self:
			for key,values in line.compute_all_tax.items():
				if 'name' in values:
					values.update({
						'invoice_code': line.invoice_code,
						'invoice_number': line.invoice_number,
						'date_invoice': line.date_invoice,
					})
				line.compute_all_tax[key] = values
