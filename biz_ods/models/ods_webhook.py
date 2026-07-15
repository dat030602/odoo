# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models, api, _
import json

_logger = logging.getLogger(__name__)

class OdsWebhook(models.Model):
	_name = 'ods.webhook'
	_description = 'Webhook'

	name = fields.Char("Name")
	json_data = fields.Text("Data")

	def create_queue_webhook(self, data):
		queue = self.sudo().create({
			'name': 'ODS Webhook',
			'json_data': json.dumps(data)
		})	
		queue.do_action_webhook()
		return True

	def do_action_webhook(self):
		datas = json.loads(self.json_data)
		check_extension = self.env['biz.ods.extension'].sudo().search([
			('ods_id', '=', datas.get('CallNumber')),
			('ods_user_id', '!=', False)
		], limit=1)
		if check_extension:
			if datas.get('Direction') == 'Outbound' and datas.get('Status') in ['Down_Out', 'Ringing_Out']:
				self.env['biz.ods.call.history'].sudo().with_env(self.env(user=check_extension.ods_user_id)).with_context(datas=datas, extension=check_extension).create_update_call_history_webhook()
				self.env['res.partner'].sudo().with_env(self.env(user=check_extension.ods_user_id)).with_context(datas=datas, extension=check_extension).create_activity_history_call()
	