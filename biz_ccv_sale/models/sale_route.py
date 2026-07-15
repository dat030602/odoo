# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
import base64
from datetime import datetime,timedelta
from odoo.exceptions import ValidationError

class SaleRoute(models.Model):
	_name = 'sale.route'
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_description = 'Sale Route'

	sequence = fields.Integer()
	stt = fields.Integer('STT', related='sequence')
	active = fields.Boolean(default=True)
	name = fields.Char('Name sale route', required=True)
	code = fields.Char('Code sale route',readonly=False,copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('sale.route'))
	user_id = fields.Many2one('res.users', 'Salesperson', default=lambda self: self.env.user.id)
	user_phone = fields.Char('Salesperson phone', related='user_id.phone')
	team_id = fields.Many2one('crm.team','Sales Team',compute='_compute_team_id',readonly=True, store=True)
	sales_team_captain_id = fields.Many2one('res.users', 'Sales Team Captain', related="team_id.user_id", store=True)
	sales_assistant_ids = fields.Many2many(related="team_id.sales_assistant_ids")
	customer_care_day  = fields.Date('Customer care day', default=lambda self: fields.Date.today())
	user_company_id = fields.Many2one('res.company',compute="_compute_company_user")
	sale_route_group_ids = fields.Many2many("sale.route.group", string='Sale route group', domain="[('company_id','in', [False, user_company_id])]")
	state = fields.Selection([
			('draft','Draft'),
			('processing','Processing'),
			('done','Done'),
			('cancel','Cancel'),
		], string="State", default='draft', tracking=True)

	note = fields.Html('Note')
	total_number_store = fields.Integer("Total number of stores", compute="compute_detail", store=True)
	total_check_in_out = fields.Integer("Total check in-out", compute="compute_detail", store=True)

	line_ids = fields.One2many("sale.route.line",'sale_route_id', string='Partner detail', copy=True)

	partner_count = fields.Integer(compute='compute_partner_count', store=True)
	checkin_count = fields.Integer(compute='compute_checkin_count', store=False)
	partner_detail_ids = fields.Many2many('res.partner',compute='compute_partner_count', store=True)
	checkin_history_ids = fields.One2many('coordinate.checkin.history','sale_route_id')
	company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

	@api.returns('self', lambda value: value.id)
	def copy(self, default=None):
		if default is None:
			default = {}
		if not default.get('name'):
			default['name'] = _("%s (copy)") % (self.name)

		return super(SaleRoute, self).copy(default)

	def _compute_company_user(self):
		for res in self:
			res.user_company_id = self.env.company.id

	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			if 'code' in vals and vals.get('code', False):
				self.check_exist_code(vals['code'])

		res = super(SaleRoute, self).create(vals_list)
		res.update_partner_route_detail()
		return res

	def write(self, vals):
		if 'code' in vals and vals.get('code', False):
			for res in self:
				res.check_exist_code(vals['code'], res.ids)

		partner_ids = self.env['res.partner']
		if 'line_ids' in vals:
			for line in vals['line_ids']:
				if line[0] == 2:
					line_id = self.env['sale.route.line'].browse(line[1])
					partner_ids += line_id.partner_id

		res = super(SaleRoute, self).write(vals)
		for sale in self:
			sale.update_partner_route_detail()

		if partner_ids:
			partner_ids.sale_route_ids = [(3, rot.id) for rot in self]
		return res

	def update_partner_route_detail(self):
		for partner in self.line_ids.mapped('partner_id'):
			if self.id not in partner.sale_route_ids.ids:
				partner.with_context(pass_update_route=True).sale_route_ids = [(4, self.id)]

	def check_exist_code(self, code, ids=False):
		domain = [('code','=', code)]
		if ids:
			domain += [('id','not in', ids)]

		ext = self.with_context(active_test=False).sudo().search(domain)
		if ext:
			raise ValidationError(_('Code sale route must be unique!'))

	@api.depends("line_ids",'line_ids.partner_id','line_ids.sale_route_report_id')
	def compute_checkin_count(self):
		self = self.sudo()
		for res in self:
			ids = res.id or res._origin.id
			partner_ids = res.line_ids.mapped('partner_id').ids
			res.checkin_count = self.env['sale.route.report'].sudo().search_count([('sale_route_id','=', ids),("partner_id",'in', partner_ids)])

	@api.depends("line_ids",'line_ids.partner_id','line_ids.sale_route_report_id')
	def compute_partner_count(self):
		for res in self:
			partner_ids = res.line_ids.mapped('partner_id').ids
			res.partner_detail_ids = [(6,0, partner_ids)]
			res.partner_count = self.env['res.partner'].search_count([("id",'in', partner_ids)])

	@api.depends('user_id')
	def _compute_team_id(self):
		for res in self:
			if not res.user_id:
				res.team_id = False
				continue

			user = res.user_id
			team = self.env['crm.team']._get_default_team_id(user_id=user.id)
			res.team_id = team.id

	@api.depends("line_ids",'line_ids.is_done_check')
	def compute_detail(self):
		for res in self:
			res.total_number_store = len(res.line_ids)
			res.total_check_in_out = len(res.line_ids.filtered(lambda x: x.is_done_check))

	def action_confirm_mass(self):
		for res in self.filtered(lambda x: x.state == 'draft'):
			res.action_confirm()

	def action_confirm(self):
		self.write({
				'state': 'processing'
			})

	def action_done_mass(self):
		for res in self.filtered(lambda x : x.state in ['draft','processing']):
			res.action_done()

	def action_cancel_mass(self):
		for res in self:
			res.action_cancel()

	def action_done(self):
		self.write({
				'state': 'done'
			})

	def action_cancel(self):
		self.write({
				'state': 'cancel'
			})

	def action_draft(self):
		self.write({
				'state': 'draft'
			})

	def action_view_partner(self):
		self = self.sudo()
		action = self.env.ref('contacts.action_contacts').sudo().read()[0]
		action['domain'] = [('id','in', self.line_ids.mapped("partner_id").ids)]
		return action

	def action_view_check_in(self):
		self = self.sudo()
		action = self.env.ref("biz_ccv_sale.action_sale_route_report_report").sudo().read()[0]
		action['domain'] = [('sale_route_id','=', self.id),('partner_id','in', self.line_ids.mapped("partner_id").ids)]
		return action

	def unlink(self):	
		for res in self:
			res.checkin_history_ids.unlink()
			for line in res.line_ids:
				line.sale_route_report_id.unlink()
			res.line_ids.unlink()
		return super(SaleRoute, self).unlink()

class SaleRouteLine(models.Model):
	_name = 'sale.route.line'
	_description = 'Sale Route Line'

	sale_route_id = fields.Many2one('sale.route', 'Sale route')
	sequence = fields.Integer('Sequence', default=1)
	stt = fields.Integer('VT Sequence', related='sequence')
	partner_id = fields.Many2one('res.partner','Partner', required=True)
	address = fields.Char('Address')
	phone = fields.Char("Phone")
	time = fields.Float('Time', related='sale_route_report_id.time')
	is_done_check = fields.Boolean('Done', copy=False, readonly=True)
	is_checkin = fields.Boolean(copy=False)
	is_checkout = fields.Boolean(copy=False)
	parent_state = fields.Selection(related='sale_route_id.state')
	sale_route_report_id = fields.Many2one('sale.route.report','Sale route report', copy=False)
	is_valid_check = fields.Boolean(compute='compute_is_valid_check')
	valid_partner = fields.Char('Valid partner', compute='compute_is_valid_check')

	@api.onchange('partner_id')
	def onchange_partner_id(self):
		if self.partner_id:
			self.update({
					'address': self.partner_id.street,
					'phone': self.partner_id.phone,
				})

	@api.depends('is_done_check','stt', 'sequence')
	def compute_is_valid_check(self):
		for res in self:
			lines = res.sale_route_id.line_ids.filtered(lambda x: not x.is_done_check and x.sequence < res.sequence)
			if lines:
				res.is_valid_check = False
				res.valid_partner = ','.join(lines.mapped('partner_id').mapped('name'))
			else:
				res.is_valid_check = True
				res.valid_partner = False

	@api.model
	def generate_checkin_history(self, line_id , image_base64, lat, long):
		line = self.browse(line_id)
		partner_id = line.partner_id
		distance = partner_id.calculate_valid_distance(lat, long)
		val = partner_id._prepare_checkin_history_value(lat, long, image_base64, distance)
		val['sale_route_id'] = line.sale_route_id.id
		history = partner_id.env['coordinate.checkin.history'].create(val)
		checkin_date = history.checkin_date and (history.checkin_date + timedelta(hours=7)) or False
		if line.sale_route_id:
			line.sale_route_id.message_post(
				body=_('Partner: %(partner)s<br/>\
					Longitude: %(longitude)s<br/>\
					Latitude: %(latitude)s<br/>\
					Check-in Date: %(checkin_date)s<br/>\
					Time: %(time)s<br/>\
					Check-in Status: %(status)s<br/>\
					Check-in Image: %(checkin_image)s',
					   partner=partner_id.name,longitude=history.Longitude, latitude=history.latitude,
					   checkin_date=checkin_date,time=0, status=history.status,
					   checkin_image=''), attachments=[('checkin_picture_%s.png' % history.id, base64.b64decode(history.checkin_image))])
		if history.status == 'successful':
			router_values = line._prepare_checkin_report_value(partner_id, lat, long, image_base64, distance)
			line.sale_route_report_id = self.env['sale.route.report'].create(router_values).id
			return True
		else:
			return False

	def _prepare_checkin_report_value(self, partner_id, latitude, longitude, image_base64, distance):
		coord_tol = self.env['coordinate.tolerancing'].search([('is_valid','=',True)], limit=1)
		r = partner_id.coordinate if partner_id.coordinate else coord_tol.allow_value if coord_tol else 0.0
		return {
			'checkin_date': fields.Datetime.now(),
			'partner_id': self.partner_id.id,
			'user_id': self.env.user.id,
			'checkin_image': image_base64,
			'checkin_latitude': latitude,
			'checkin_longitude': longitude,
			'checkin_status': 'successful' if distance*1000 <= r else 'failed',
			'sale_route_line_id': self.id,
		}

	def generate_checkout_history(self, line_id, image_base64, lat, long):
		line = self.browse(line_id)
		partner_id = line.partner_id
		distance = partner_id.calculate_valid_distance(lat, long)
		val = partner_id._prepare_checkin_history_value(lat, long, image_base64, distance)
		val['sale_route_id'] = line.sale_route_id.id
		history = partner_id.env['coordinate.checkin.history'].create(val)
		checkin_date = history.checkin_date and (history.checkin_date + timedelta(hours=7)) or False
		if line.sale_route_id:
			line.sale_route_id.message_post(
				body=_('Partner: %(partner)s<br/>\
					Longitude: %(longitude)s<br/>\
					Latitude: %(latitude)s<br/>\
					Check-out Date: %(checkin_date)s<br/>\
					Time: %(time)s<br/>\
					Check-out Status: %(status)s<br/>\
					Check-out Image: %(checkin_image)s',
					   partner=partner_id.name,longitude=history.Longitude, latitude=history.latitude,
					   checkin_date=checkin_date,time=0, status=history.status,
					   checkin_image=''), attachments=[('checkin_picture_%s.png' % history.id, base64.b64decode(history.checkin_image))])
		if history.status == 'successful':
			router_values = line._prepare_checkout_report_value(partner_id, lat, long, image_base64, distance)
			line.sale_route_report_id.write(router_values)
			line.write({
				'is_done_check': True
			})
			return True
		else:
			return False

	def _prepare_checkout_report_value(self, partner_id, latitude, longitude, image_base64, distance):
		coord_tol = self.env['coordinate.tolerancing'].search([('is_valid','=',True)], limit=1)
		r = partner_id.coordinate if partner_id.coordinate else coord_tol.allow_value if coord_tol else 0.0
		return {
			'checkout_date': fields.Datetime.now(),
			'checkout_image': image_base64,
			'checkout_latitude': latitude,
			'checkout_longitude': longitude,
			'checkout_status': 'successful' if distance*1000 <= r else 'failed',
			'sale_route_line_id': self.id,
		}