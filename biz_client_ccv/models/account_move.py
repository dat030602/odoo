# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from functools import lru_cache

class AccountMove(models.Model):
	_inherit = "account.move"

	journal_id = fields.Many2one(
		'account.journal',
		domain="[('id', '!=', False)]",
	)
	exchange_rate = fields.Many2one('res.currency.rate',string="Exchange rate")
	partner_bank_id =fields.Many2one('res.partner.bank', string="Recipient Bank Account")
	number_ctnb = fields.Char('Number CTNB')
	series = fields.Char('Series')

	@api.onchange('exchange_rate')
	def onchange_exchange_rate(self):
		for res in self:
			if res.exchange_rate:
				for line in res.line_ids:
					line.currency_id = res.exchange_rate.currency_id
					line._compute_currency_rate()
					line._inverse_amount_currency()
					
	def create_new_exchange_rate(self):
		view_id = self.env.ref('base.view_currency_rate_form').id
		
		return {
			'type': 'ir.actions.act_window',
			'name': 'Currency Rate Form',
			'view_mode': 'form',
			'res_model': 'res.currency.rate',
			'views': [(view_id, 'form')],
			'target': 'new',
			'context': {
				'default_currency_id': self.currency_id.id,
				'create_exchange_rate_id': self.id,
				'model': 'account.move',
			},
		}

class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	def _get_conversion_rate_custom(self, from_currency, to_currency, company, date):
		currency_rates = from_currency._get_rates(company, date)
		res = to_currency / currency_rates.get(from_currency.id)
		return res

	@api.depends('currency_id', 'company_id', 'move_id.date')
	def _compute_currency_rate(self):
		super(AccountMoveLine,self)._compute_currency_rate()
		for line in self:
			if line.move_id and line.move_id.exchange_rate:
				line.currency_rate = self._get_conversion_rate_custom(
					from_currency=line.company_currency_id,
					to_currency=line.move_id.exchange_rate.rate,
					company=line.company_id,
					date=line.move_id.exchange_rate.name)
							   
