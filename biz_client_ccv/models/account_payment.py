# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from functools import lru_cache

class AccountPayment(models.Model):
	_inherit = "account.payment"
	
	bank_account_contact_id =fields.Many2one('res.partner.bank', string="Bank Account Contact", domain="[('id', 'in', partner_bank_contact_ids)]")
	partner_bank_contact_ids = fields.Many2many(
		comodel_name='res.partner.bank',
		compute='_compute_partner_bank_contact_ids',
	)
	exchange_rate = fields.Many2one('res.currency.rate',string="Exchange rate")
 
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
				'model': 'account.payment',
			},
		}
  
	@api.depends('partner_id', 'company_id')
	def _compute_partner_bank_contact_ids(self):
		for pay in self:
			pay.partner_bank_contact_ids = pay.partner_id.bank_ids.filtered(lambda x: x.company_id.id in (False, pay.company_id.id))._origin