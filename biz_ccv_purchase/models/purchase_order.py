# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta

from markupsafe import escape, Markup
from pytz import timezone, UTC
from werkzeug.urls import url_encode

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError
from odoo.addons.biz_ccv_purchase.config import amount_to_text

def get_address(partner_id):
	if not partner_id:
		return ''
	address_parts = []
	
	if partner_id.street:
		address_parts.append(partner_id.street)
	
	if partner_id.wards_id:
		address_parts.append(partner_id.wards_id.name) 
	
	if partner_id.district_id:
		address_parts.append(partner_id.district_id.name)
	
	if partner_id.state_id:
		address_parts.append(partner_id.state_id.name)
	
	if partner_id.country_id:
		address_parts.append(partner_id.country_id.name)

	full_address = ', '.join(address_parts)
	return full_address

class PurchaseOrder(models.Model):
	_inherit = "purchase.order"

	delivery_location = fields.Char('Delivery Location')
	payment_note = fields.Char("Payment")
	supplier_contact = fields.Char("Supplier Contact")
	supplier_phone = fields.Char("Supplier phone")
	ccv_contract_id = fields.Many2one('res.partner',"CCV Contact", domain='[("is_user_contact","=", True)]', default=lambda self: self.env.user.partner_id)
	supplier_represent = fields.Char("Supplier representative")
	ccv_represent_id = fields.Many2one('res.partner',"CCV representative", domain='[("is_user_contact","=", True)]')
	note = fields.Char("Note", default="Giá chưa gồm thuế VAT")
	requirements = fields.Text("Requirements")

	def get_po_ccv_report_name(self):
		date_now = datetime.now()  + timedelta(hours=7)
		return "COCOVA_%s_P.TM_%s" % (date_now.strftime('%d/%m/%Y'), self.name)

	def get_custom_py3o_context(self):	
		date_now = datetime.now()  + timedelta(hours=7)

		amount_untaxed = self.amount_total
		if amount_untaxed % 1 == 0:
			amount_total_text = amount_to_text(self.amount_total) +  ' đồng chẵn'
		else:
			mod = round((amount_untaxed % 1) * 100, 2)
			div = amount_untaxed // 1
			amount_total_text = "%s lẻ %s đồng" % (amount_to_text(div), amount_to_text(mod).lower())

		return {
			'object': self,
			'date_approve': self.date_approve and self.date_approve.strftime('%d/%m/%Y') or '',
			'date_planned': self.date_planned and self.date_planned.strftime('%d/%m/%Y') or '',
			'date_now': date_now.strftime('%d/%m/%Y'),
			'format_number': self.format_number,
			'amount_total_text': amount_total_text,
			'get_ccv_contract': self.get_ccv_contract(),
			'partner_address': get_address(self.partner_id),
			'company_address': get_address(self.company_id),
			'ccv_contract_id': self.ccv_contract_id and  self.ccv_contract_id.user_ids[:1].name_without_position or '',
			'ccv_represent_id': self.ccv_represent_id and  self.ccv_represent_id.user_ids[:1].name_without_position or '',
			'taxes': [
				{
					'name': 'Thuế suất %s%%' % int(tax.amount),
					'amount': sum(self.order_line.filtered(lambda l: tax in l.taxes_id).mapped('price_tax')),
				} for tax in self.order_line.taxes_id
			]
		}

	def get_ccv_contract(self):
		for res in self:
			contract = []
			if res.ccv_contract_id:
				if res.ccv_contract_id.name:
					contract.append(str(res.ccv_contract_id.name))
				if res.ccv_contract_id.phone:
					contract.append(str(res.ccv_contract_id.phone)) 
			contract = ' - '.join(contract)
			return contract
   
	def format_number(self, number):
		number_format = ''
		if number:
			if number % 1 == 0:
				number_format = "{:,.0f}".format(number).replace(',', '.')
			else:
				number_format = "{:,.2f}".format(number).rstrip('0').replace(',', '.')
		return number_format

	def action_create_invoice_ccv(self):
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		self.ensure_one()
		if self.invoice_status != 'to invoice':
			raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

		lines = []

		for line in self.order_line:
			if line.display_type == 'line_section':
				continue

			if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
				lines.append(line)

		if not lines:
			raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

		return {
			'name': _('Select products'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'wz.purchase.invoive',
			'target': 'new',
			'context': {
				'default_purchase_id': self.id,
				'default_order_line': [(0,0, {
						"purchase_line_id": line.id,
						"is_selected": True,
					}) for line in lines]
			}
		}

	def action_done_create_invoice_ccv(self, lines):
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		invoice_vals_list = []
		sequence = 10
		if self.invoice_status != 'to invoice':
			raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

		order = self.with_company(self.company_id)
		invoice_vals = self._prepare_invoice()

		for line in lines:
			if line.display_type == 'line_section':
				continue
				
			if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
				line_vals = line._prepare_account_move_line()
				line_vals.update({'sequence': sequence})
				invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
				sequence += 1

		invoice_vals_list.append(invoice_vals)

		if not invoice_vals_list:
			raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

		new_invoice_vals_list = []
		for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
			origins = set()
			payment_refs = set()
			refs = set()
			ref_invoice_vals = None
			for invoice_vals in invoices:
				if not ref_invoice_vals:
					ref_invoice_vals = invoice_vals
				else:
					ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
				origins.add(invoice_vals['invoice_origin'])
				payment_refs.add(invoice_vals['payment_reference'])
				refs.add(invoice_vals['ref'])
			ref_invoice_vals.update({
				'ref': ', '.join(refs)[:2000],
				'invoice_origin': ', '.join(origins),
				'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
			})
			new_invoice_vals_list.append(ref_invoice_vals)
		invoice_vals_list = new_invoice_vals_list

		moves = self.env['account.move']
		AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
		for vals in invoice_vals_list:
			moves |= AccountMove.with_company(vals['company_id']).create(vals)

		moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()
		return self.action_view_invoice(moves)