# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,  _
from odoo.exceptions import UserError, ValidationError
import json
import requests

class ConveyorLog(models.Model):
	_name = 'conveyor.log'
	_description = 'Conveyor log'
	_order = "create_date desc"

	name = fields.Char("Name")
	picking_id = fields.Many2one("stock.picking", 'Picking')
	url = fields.Char("Url")
	headers = fields.Text("Headers")
	payload = fields.Text('Payload')
	params = fields.Text("Params")	
	response = fields.Text("Response")
	state = fields.Selection([
			('new','New'),
			('done','Done'),
			('error','Error'),
		], string="State", default="new")
	error = fields.Text("Error")
	is_push = fields.Boolean("Is push")

	def execute_api(self, record, params={}, data={}, is_push=False):
		headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
		'Accept': '*/*',
		}
		url = 'http://maydemccv.com/sharedata.php'

		queue = self.create({
			'name': url,
			'url': url,
			'headers': json.dumps(headers),
			'payload': json.dumps(data),
			'params': json.dumps(params),
			'url': url,
			# 'picking_id': record.id,
			'is_push': is_push
		})
		return queue.do_action()

	def do_action(self):
		company_id = self.env.company
		result = False
		error = False
		response_data = False
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
			'Accept': '*/*',
		}
		data = json.loads(self.payload)
		try:
			result = requests.post(self.url, headers=headers, data=data, auth=(company_id.conveyor_username, company_id.conveyor_password))
			if result.status_code != 200:
				raise ValidationError(result.text)

			self.write({
				'state': 'done',
				'response': result and result.text or False
			})
			
			# Parse response safely
			if result and result.text:
				try:
					response_data = json.loads(result.text)
				except json.JSONDecodeError:
					response_data = False
		except Exception as e:
			error = e
			self.write({
				'state': 'error',
				'response': result and result.text or False,
				'error': str(error)
			})

		return {
			'data': response_data,
			'error': error,
			'queue': self.id
		}