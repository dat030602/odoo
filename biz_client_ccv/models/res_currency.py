# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.res_currency import Currency as ORIGIN_Currency

class ResCurrencyCCV(models.Model):
	_inherit = 'res.currency'
	
	# bỏ thông báo ko được sửa số thập phân trong tiền tệ
	def write(self, vals):
		res = super(ORIGIN_Currency, self).write(vals)
		return res

ORIGIN_Currency.write = ResCurrencyCCV.write

class CurrencyRate(models.Model):
	_inherit = "res.currency.rate"

	def name_get(self):
		result = []
		for res in self:
			result.append((res.id, "%s %s" % (res.currency_id.name or '',res.inverse_company_rate)))
		return result

	_sql_constraints = [
		('unique_name_per_day', 'CHECK(1=1)', 'Not error'),
	]

	@api.model_create_multi
	def create(self, vals_list):
		res = super().create(vals_list)
		for rec in res:
			search_self = self.search([('id','!=',rec.id),('currency_id','=',rec.currency_id.id),('name','=',rec.name)],limit=1)
			if search_self:
				raise ValidationError(_('Same day same exchange rate. Please check again!'))

			if rec.env.context.get('create_exchange_rate_id') and rec.env.context.get('model') == 'account.move':
				record = rec.env['account.move'].browse(rec.env.context['create_exchange_rate_id'])
				record.exchange_rate = res.id
			elif rec.env.context.get('create_exchange_rate_id') and rec.env.context.get('model') == 'account.payment':
				record = rec.env['account.payment'].browse(rec.env.context['create_exchange_rate_id'])
				record.exchange_rate = res.id
				
		return res

	@api.model
	def search(self, args, offset=0, limit=None, order=None, count=False):
		ctx = self._context
		if 'order_display' in ctx:
			order = ctx['order_display']
		return super(CurrencyRate, self).search(
			args, offset=offset, limit=limit, order=order, count=count)
