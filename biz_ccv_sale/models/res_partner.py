from odoo import api, fields, models,_
from urllib.request import urlopen
import json
import base64
import requests
from odoo.tools import float_round
from odoo.exceptions import UserError, ValidationError
from math import radians, cos, sin, asin, sqrt
LOC_URL = 'http://ipinfo.io/json'
RADIO = 6371

from datetime import timedelta

class ResPartner(models.Model):
	_inherit = "res.partner"

	def _default_coordinate(self):
		coordinate = self.env['coordinate.tolerancing'].search([('is_valid', '=', True)], limit=1)
		return coordinate.allow_value if coordinate else 0.0

	checkin_history_ids = fields.One2many('coordinate.checkin.history', 'partner_id', 'Coordinate Checkin History')
	checkin_history_count = fields.Integer(string="Coordinate Checkin History Count", compute="_compute_checkin_history")
	coordinate = fields.Float('Coordinate Tolerancing(m)', default=_default_coordinate)
	code_contact = fields.Char(string='Code Contact', required=True, index=True)
	property_account_expense_id = fields.Many2one('account.account', company_dependent=True,
		string="Tài khoản chi phí",
		domain="[('deprecated', '=', False), ('company_id', '=', allowed_company_ids[0])]",
		help="Tài khoản này sẽ được sử dụng thay cho tài khoản mặc định của sản phẩm nếu được thiết lập.")
	name_contact = fields.Char(string='Contact type name')
	code_type_contact = fields.Char(string='Contact type code')
	
	fax = fields.Char(string="Fax")
	representative = fields.Char(string="Representative")
	representative_phone = fields.Char(string="Representative phone number")
	sale_route_ids = fields.Many2many('sale.route','rel_partner_sale_route','partner_id','sale_route_id', string="Sale route")
	hide_interface = fields.Boolean(compute='_compute_hide_interface')


	def _compute_hide_interface(self):
		for partner in self:
			partner.hide_interface = True if not self.env.user.has_group('sales_team.group_sale_salesman') else False

	def _compute_checkin_history(self):
		data = self.env["coordinate.checkin.history"].read_group(
			[('partner_id', '=', self.id)],
			["ids:array_agg(id)", "partner_id"],
			["partner_id"],
		)
		mapped_count = {d["partner_id"][0]: d["partner_id_count"] for d in data}
		for prop_type in self:
			prop_type.checkin_history_count = mapped_count.get(prop_type.id, 0)

	# Inherit
	@api.depends('is_company', 'name', 'parent_id.display_name', 'type', 'company_name', 'code_contact')
	def _compute_display_name(self):
		super(ResPartner, self)._compute_display_name()

	@api.onchange('user_id')
	def onchange_user_id(self):
		team_ids = []
		result = {'domain': {'team_id': []}}
		if self.user_id:
			team_ids = self.env['crm.team'].search([('member_ids','in',self.user_id.ids)])
			if self.team_id not in team_ids:
				self.team_id = False

		if team_ids:
			self.team_id = team_ids[0]
			result = {'domain': {'team_id': [('id', 'in', team_ids.ids)]}}
		return result

	def _get_name(self):
		partner = self
		name = super()._get_name()
		code_contact = partner.code_contact or ''

		if code_contact:
			name = f"[{code_contact}] {name}"
		return name


	def _check_duplicate_contact_code(self):
		for contact in self:
			if self.search_count([('code_contact', '=', contact.code_contact)]) > 1:
				raise ValidationError(_('The contact code already exists, please check again'))
	
	@api.model_create_multi
	def create(self, value):
		partners = super(ResPartner, self).create(value)
		for partner in partners:
			if partner.code_contact:
				partner._check_duplicate_contact_code()

			if partner.sale_route_ids:
				partner.update_sale_route_detail()

		return partners

	def write(self, vals):
		old_coordinates = {}
		for partner in self:
			partner_latitude = vals.get('partner_latitude', partner.partner_latitude)
			partner_longitude = vals.get('partner_longitude', partner.partner_longitude)
			if any(field in vals for field in ['street', 'wards_id', 'district_id', 'state_id', 'country_id', 'city']) \
					and not all('partner_%s' % field in vals for field in ['latitude', 'longitude']):
				self = self.with_context(skip_create_nolog=True)
				partner_latitude = float_round(vals['partner_latitude'] if 'partner_latitude' in vals else partner.partner_latitude, precision_digits=7)
				partner_longitude = float_round(vals['partner_longitude'] if 'partner_longitude' in vals else partner.partner_longitude, precision_digits=7)
			elif any(field in vals for field in ['street', 'wards_id', 'district_id', 'state_id', 'country_id', 'city']):
				partner_latitude = float_round(partner_latitude, precision_digits=7)
				partner_longitude = float_round(partner_longitude, precision_digits=7)

			old_coordinates[partner.id]  = {
				'partner_latitude': partner_latitude,
				'partner_longitude': partner_longitude
			}

		old_check  = False

		if 'sale_route_ids' in vals:
			for partner in self:
				if vals['sale_route_ids'][0][0] == 6:
					new_ids = vals['sale_route_ids'][0][2]
					old_check = partner.sale_route_ids.filtered(lambda x: x.id not in new_ids)
					for route in old_check:
						for line in route.line_ids.filtered(lambda x: x.partner_id.id == partner.id):
							if line.sale_route_report_id:
								raise ValidationError(_("Completed sales route cannot be deleted"))

		record = super(ResPartner, self).write(vals)

		for partner in self:
			if partner.code_contact:
				partner._check_duplicate_contact_code()

			if 'sale_route_ids' in vals and not self._context.get('pass_update_route',False):
				partner.update_sale_route_detail()

			if old_check:
				for check in old_check:
					check.line_ids.filtered(lambda x: x.partner_id.id == partner.id).unlink()
			
			old_coordinates_partner = old_coordinates.get(partner.id)

			if any(field in vals for field in ['street', 'wards_id', 'district_id', 'state_id', 'country_id', 'city']):
				partner.update({
					'partner_latitude': old_coordinates_partner['partner_latitude'],
					'partner_longitude': old_coordinates_partner['partner_longitude']
				})

		return record

	def update_sale_route_detail(self):
		for route in self.sale_route_ids:
			if not any(line.partner_id.id == self.id for line in route.line_ids):
				route.line_ids = [(0,0,{
						'partner_id': self.id,
						'address': self.street,
						'phone': self.phone
					})]

	def get_location_address(self):
		"""
			return Latitude, Longitude
		"""
		try:
			response = urlopen(LOC_URL)
		except Exception as e:
			raise ValidationError(e)

		data = json.load(response)
		loc = data.get('loc').split(',')
		return loc[0], loc[1]

	def _prepare_checkin_history_value(self, latitude, Longitude, image_base64, distance):
		coord_tol = self.env['coordinate.tolerancing'].search([('is_valid','=',True)], limit=1)
		r = self.coordinate if self.coordinate else coord_tol.allow_value if coord_tol else 0.0

		return {
			'checkin_date': fields.Datetime.now(),
			'partner_id': self.id,
			'user_id': self._uid,
			'checkin_image': image_base64,
			'latitude': latitude,
			'Longitude': Longitude,
			'status': 'successful' if distance*1000 <= r else 'failed' # convert km->m
		}

	def calculate_valid_distance(self, lat_y, long_y):
		coord_tol = self.env['coordinate.tolerancing'].search([('is_valid','=',True)], limit=1)
		r = self.coordinate if self.coordinate else coord_tol.allow_value if coord_tol else 0.0

		lat_x = self.partner_latitude or 0.0
		long_x = self.partner_longitude or 0.0
		lon1, lat1, lon2, lat2 = map(radians, [float(long_x), float(lat_x), float(long_y), float(lat_y)])
		dlon = lon2 - lon1
		dlat = lat2 - lat1
		a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
		c = 2 * asin(sqrt(a))
		return c*RADIO

	def _generate_checkin_history(self, lat, long, image_base64):
		distance = self.calculate_valid_distance(lat, long)
		val = self._prepare_checkin_history_value(lat, long, image_base64, distance)
		checkin_history = self.env['coordinate.checkin.history'].create(val)
		checkin_date = checkin_history.checkin_date and checkin_history.checkin_date + timedelta(hours=7) or False
		self.message_post(
			body=_('Longitude: %(longitude)s<br/>Latitude: %(latitude)s<br/>Check-in Date: %(checkin_date)s<br/>Status: %(status)s<br/>Check-in Image: %(checkin_image)s',
				   longitude=checkin_history.Longitude, latitude=checkin_history.latitude,
				   checkin_date=checkin_date, status=checkin_history.status,
				   checkin_image=''), attachments=[('checkin_picture_%s.png' % checkin_history.id, base64.b64decode(checkin_history.checkin_image))])

	@api.model
	def action_check_in(self, parnter_id):
		parnter_id = self.browse(parnter_id)
		check_coordinates_received = {'error': False}
		if parnter_id and not parnter_id.partner_latitude or not parnter_id.partner_longitude:
			check_coordinates_received.update({
				'error': True,
				'error_name': _('Agency location not updated enough information, Please check again!')
			})
			return check_coordinates_received

		lat, long = parnter_id.get_location_address()

		if lat and long:
			check_coordinates_received.update({
				'lat': lat,
				'long': long,
				'have_lat_long': True
			})
		return check_coordinates_received

	def action_view_check_in(self):
		res = self.env.ref("biz_ccv_sale.action_coordinate_checkin_history").sudo().read()[0]
		res["domain"] = [("id", "in", self.checkin_history_ids.ids)]
		return res

	@api.model
	def generate_checkin_history(self, parnter_id, img_data_base64, lat, long):
		parnter_id = self.browse(parnter_id)
		if parnter_id:
			parnter_id._generate_checkin_history(lat, long, img_data_base64)
			return True

	@api.onchange('street', 'zip', 'city', 'state_id', 'country_id')
	def _delete_coordinates(self):
		pass
