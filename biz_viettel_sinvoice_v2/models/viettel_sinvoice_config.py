from odoo import api,fields, models, _
import re
import json, urllib.parse
from odoo.exceptions import UserError, ValidationError
import requests
import sys
import logging
import smtplib
from socket import gaierror, timeout
from ssl import SSLError
import html2text
import idna
from dateutil.relativedelta import relativedelta
from odoo.tools import ustr
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
BIZAPPS_SERVER_URL = 'https://bizapps.vn'
BIZAPPS_SERVER_TEST_URL = 'http://localhost:8088'

from odoo import release

_logger = logging.getLogger(__name__)
_test_logger = logging.getLogger('odoo.tests')

SMTP_TIMEOUT = 60
PY3 = sys.version_info >= (3,0)
from datetime import date, datetime

if PY3:
	unichr = chr
	xrange = range
	unicode = str
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
try:
	requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'HIGH:!DH:!aNULL'
except AttributeError:
	# no pyopenssl support used / needed / available
	pass
	
class ViettelSinvoiceConfig(models.Model):
	_name = 'viettel.sinvoice.config'
	_description = 'Viettel S-Invoice Configuration'
	_rec_name = 'vsi_type'

	vsi_domain = fields.Char('Domain', default="https://api-sinvoice.viettel.vn:443")
	vsi_tin = fields.Char('TIN', default='0101159195')
	vsi_username = fields.Char('Username', default='0100109106-505')
	vsi_password = fields.Char('Password', default='123456a@A')
	vsi_template = fields.Char('Template', default='01GTKT0/003')
	vsi_series = fields.Char('Series', default='DH/19E')
	vsi_type = fields.Many2one('viettel.sinvoice.type', 'Invoice Type')
	vsi_access_token = fields.Text('SInvoice Token')
	vsi_refresh_token = fields.Text('SInvoice Refresh Token')
	vsi_expires_in = fields.Integer('SInvoice Expires In')
	vsi_connected = fields.Boolean('SInvoice connected')
	company_id = fields.Many2one('res.company','Company', default=lambda self: self.env.company.id)
	state = fields.Selection([
		('draft','Draft'),
		('error','Error'),
		('connected', 'Connected')
	], default='draft')

	allow_create_odoo_inv_adjust = fields.Boolean("Allows creating Odoo invoices when making adjustments", default=False)
	vsi_uncheck_data = fields.Boolean("Uncheck data")

	@api.onchange('company_id')
	def onchange_company_id(self):
		for res in self:
			if res.company_id:
				res.vsi_tin = res.company_id.vat

	def vsi_get_customer_fields(self):
		if self.vsi_type and self.vsi_template:
			self.vsi_type.sudo().vsi_get_customer_fields(self,self.vsi_template) 
	
	def check_vsi_server(self):
		if not self.vsi_tin:
			raise UserError(_("Please check TIN!"))
		vsi_type = self.vsi_type
		vsi_template = self.vsi_template
		vsi_series = self.vsi_series
		error_text = _("Please check %s")

		if not vsi_type:
			raise UserError(error_text%_('Invoice Type'))
		if not vsi_template:
			raise UserError(error_text%_('Template'))
		if not vsi_series:
			raise UserError(error_text%_('Series'))

		if not self.vsi_connected:
			self.sinvoice_refresh_token()
		succeed = ''
		try:
			api_url = '/services/einvoiceapplication/api/InvoiceAPI/InvoiceUtilsWS/getProvidesStatusUsingInvoice'
			params = {
				"supplierTaxCode": self.vsi_tin,
				"templateCode": vsi_template,
				"serial": vsi_series,
			}
			headers = {
				'Content-Type': 'application/json',
			}

			result = self.execute_request(self, 'POST', api_url, headers=headers, data=params)

			if result.get('success', False):
				output = result['data']
				if not output['errorCode'] and not output['description']:
					succeed = _("Invoice number used %s / %s") % (output['numOfpublishInv'], output['totalInv'])
			else:
				self.write({
					"vsi_connected": False,
					'state': 'error'
				})
				self.env.cr.commit()
				raise UserError("Errors: (%s)" % (result['error']))

		except UserError as e:
			raise e
		except (UnicodeError, idna.core.InvalidCodepoint) as e:
			raise UserError(_("Invalid server name !\n %s")% ustr(e))
		except (gaierror, timeout) as e:
			raise UserError(_("No response received. Check server address and port number.\n %s")% ustr(e))
		except SSLError as e:
			raise UserError(_("An SSL exception occurred. Check connection security type.\n %s")% ustr(e))
		except Exception as e:
			raise UserError(_("Connection Test Failed! Here is what we got instead:\n %s") % ustr(e))
		finally:
			pass

		self.write({
				'vsi_connected': True,
				'state': 'connected'
			})

		message = _("""Connection Test Succeeded! Everything seems properly set up!
			%s""") % succeed or ''
		title = _("Connection Test Succeeded!")
		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'title': title,
				'message': message,
				'sticky': False,
			}
		}

	def sinvoice_refresh_token(self):
		if not self.vsi_tin:
			raise UserError(_("Please check TIN!"))
		vsi_type = self.vsi_type
		vsi_template = self.vsi_template
		vsi_series = self.vsi_series
		error_text = _("Please check %s")

		if not vsi_type:
			raise UserError(error_text%_('Invoice Type'))
		if not vsi_template:
			raise UserError(error_text%_('Template'))
		if not vsi_series:
			raise UserError(error_text%_('Series'))

		params = {
			"username": self.vsi_username,
			"password": self.vsi_password,
		}
		api_url = self.vsi_domain + '/auth/login'
		headers = {
			'Content-Type': 'application/json'
		}
		succeed = ''
		try:
			response = requests.request("POST", api_url, headers=headers, data=json.dumps(params))
			data = response.json()
			if response.status_code == 200:
				if data.get('access_token',False):
					self.write({
						"vsi_access_token": data.get('access_token'),
						"vsi_refresh_token": data.get('refresh_token'),
						"vsi_expires_in": data.get('expires_in'),
						"vsi_connected": True,
						'state': 'connected'
					})
					self.env.cr.commit()
			else:
				detail = data.get('detail', '') or data.get('error', '') or data.get('error_description', '')
				title = data.get('title', '') or data.get('message', '')
				detail_error = ""
				self.write({
					"vsi_connected": False,
					'state': 'error'
				})
				self.env.cr.commit()
				raise UserError("Errors: (%s) %s %s" % (response.status_code, title, detail))
		except UserError as e:
				# let UserErrors (messages) bubble up
			raise e
		except (UnicodeError, idna.core.InvalidCodepoint) as e:
			raise UserError(_("Invalid server name !\n %s")% ustr(e))
		except (gaierror, timeout) as e:
			raise UserError(_("No response received. Check server address and port number.\n %s")% ustr(e))
		except SSLError as e:
			raise UserError(_("An SSL exception occurred. Check connection security type.\n %s")% ustr(e))
		except Exception as e:
			raise UserError(_("Connection Test Failed! Here is what we got instead:\n %s") % ustr(e))
		finally:
			pass

		return True

	def execute_request(self, record, method, url, headers={}, data={}, params={}, urlencoded=False):
		expires_date = self.env['ir.config_parameter'].sudo().get_param('viettel.expire_date', False)
		if not expires_date:
			expires_date = self.update_biz_expires_date()

		expires_date = datetime.strptime(expires_date ,DEFAULT_SERVER_DATETIME_FORMAT)
		if expires_date <= datetime.now():
			raise ValidationError(_('Module has expired.Please contact your administrator.'))			

		if not self:
			raise ValidationError(_('Please configure Viettel S-Invoice server'))

		if not self.vsi_access_token:
			raise UserError(_("Please connect Viettel S-Invoice server first!"))

		api_url = self.vsi_domain + url
		Queue = self.env['viettel.sinvoice.queue'].sudo()
		queue_id = Queue.create({
			'name': 'V-Invoice Queue',
			'url': api_url,
			'headers': headers,
			'method': method,
			'data': data,
			'params': params,
			'config_id': self.id,
			'model': record._name,
			'res_ids': record.ids,
			'urlencoded': urlencoded
		})
		return queue_id.do_action()

	def update_biz_expires_date(self):
		db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid') or False
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

		url = BIZAPPS_SERVER_URL + '/saas/sinvoice/register'

		payload = {
			'db_uuid': db_uuid,
			'base_url': base_url,
			'database': self.env.cr.dbname,
			'server_version': release.version,
			'sinvoice_type': 'viettel'
		}

		headers = {
			'Content-Type': 'application/json'
		}
		expires_date = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
		try:
			response = requests.post(url, headers=headers, data=json.dumps(payload))
			res = json.loads(response.text)
			result = res['result']
			if result.get('success', True):
				data_new = result['date_expired']
				self.env['ir.config_parameter'].sudo().set_param('viettel.expire_date', data_new)
				expires_date = data_new
		except Exception as e:
			self.env['ir.config_parameter'].sudo().set_param('viettel.expire_date', False)
			pass

		return expires_date
