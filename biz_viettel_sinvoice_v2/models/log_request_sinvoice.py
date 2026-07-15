# -*- coding: utf-8 -*-
from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import json
import requests
from dateutil.relativedelta import relativedelta

from ast import literal_eval

class LogRequestSinvoice(models.Model):
	_name = 'log.request.sinvoice'
	_description  = "log.request.sinvoice"

class ViettelSinvoiceQueue(models.Model):
	_name = 'viettel.sinvoice.queue'
	_description = "Log Request Sinvoice"
	_order = "create_date desc"

	name = fields.Char('Name')
	url = fields.Char('Url')
	model  = fields.Char(string="Model")
	method = fields.Char('Method')
	res_ids = fields.Char("IDS")
	headers = fields.Text('Headers')
	data = fields.Text('Data')
	params = fields.Text('Params')
	response = fields.Text('Response')
	message = fields.Text('Message')
	error = fields.Text(string="Error")
	urlencoded = fields.Boolean("Urlencoded")
	config_id  = fields.Many2one("viettel.sinvoice.config")
	state = fields.Selection([
			('new','New'),
			('error','Error'),
			('done','Done'),
		], string="State", default='new')

	def do_action(self):
		config_id = self.config_id
		headers = literal_eval(self.headers)
		body = literal_eval(self.data)
		params = literal_eval(self.params)

		headers.update({
			'Authorization': 'Bearer %s' % config_id.vsi_access_token,
		})
		payload = body 
		if not self.urlencoded:
			payload = body and json.dumps(body) or None

		data = {}
		try:
			response = requests.request(self.method, self.url, headers=headers, data=payload, params=params)
			data = json.loads(response.text)
			if response.status_code != 200:
				if response.status_code == 401 and data.get('error', '') == 'invalid_token':
					if config_id.sinvoice_refresh_token():
						return self.do_action()
				raise ValidationError(data)

			data_update = {
				'state': 'done',
				'message': 'Oke',
				'response': data,
			}
			data_response = {
				'success': True,
				'data': data or {},
			}
		except Exception as e:
			data_update = {
				'state': 'error',
				'error': e,
				'message': e,
				'response': data,
			}
			data_response = {
				'success': False,
				'error': e,
				'data': {}
			}

		self.write(data_update)
		self.env.cr.commit()
		return data_response

	def _cron_delete_sinvoice_queue(self):
		pdf_now = datetime.now() - relativedelta(days=2)
		pdf_ids = self.sudo().search([
				('url','ilike','InvoiceUtilsWS/getInvoiceRepresentationFile'),
				('create_date','<=', pdf_now)
			])

		pdf_ids.sudo().unlink()
		date_now = datetime.now() - relativedelta(months=2)
		done_ids = self.sudo().search([
				('state','=','done'),
				('create_date','<=', date_now)
			])
		done_ids.sudo().unlink()