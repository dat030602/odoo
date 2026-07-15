# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import werkzeug
from odoo.addons.web.controllers.home import ensure_db, Home
from odoo.addons.base_setup.controllers.main import BaseSetup
from odoo.exceptions import UserError
from odoo.http import request
from odoo import http
from odoo.exceptions import ValidationError
from datetime import datetime,timedelta

class HomeController(Home):

	@http.route('/check_popup_change_password', type='json', auth='public', website=True)
	def check_popup_change_password(self, **post):
		search_user = request.env['res.users'].sudo().search([('login','=',post.get('login'))],limit=1)
		if search_user and search_user.state == 'new' and not search_user.update_passwd:
			return True
		return False

	@http.route('/change_password_popup', type='json', auth='public', website=False)
	def change_password_popup(self, **post):
		try:
			user_id = request.env['res.users'].sudo().search([('login','=',post.get('login')),('state','=','new')],limit=1)
			if not user_id:
				raise ValidationError(_('Something went wrong, please try again'))
			user_id._change_password(post.get('passwd'))
			user_id.update_passwd = True
		except Exception as e:
			return {
				'error': str(e),
				'success': False
			}
		return {
			'success': True
		}

