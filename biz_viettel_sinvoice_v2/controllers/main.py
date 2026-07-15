from odoo import http, _
from odoo.addons.web.controllers.main import ensure_db, Home
import json
from odoo.http import request

class SaasViettel(http.Controller):
	@http.route('/saas/viettel/update-expired', type='json', auth='public', methods=["POST"], csrf=False)
	def update_expired(self, **kwargs):
		response = {
			'success': True
		}
		data = json.loads(request.httprequest.data.decode('utf-8'))
		request.env['ir.config_parameter'].sudo().set_param('viettel.expire_date', data['date_expired'])

		return response