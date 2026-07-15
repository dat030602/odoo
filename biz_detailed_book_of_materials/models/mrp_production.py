# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

class MrpProduction(models.Model):
	_inherit = 'mrp.production'

	interpretation = fields.Text("Interpretation")

	# --- Các trường chữ ký ---
	preparer_id = fields.Many2one('res.users', string='Người lập', default=lambda self: self.env.user)
	supervisor_id = fields.Many2one(
		'res.users', string='Giám sát',
		compute='_compute_supervisor_id', store=True, readonly=False
	)

	@api.depends('picking_type_id', 'picking_type_id.supervisor_id')
	def _compute_supervisor_id(self):
		for rec in self:
			if rec.picking_type_id and 'supervisor_id' in rec.picking_type_id._fields:
				rec.supervisor_id = rec.picking_type_id.supervisor_id
	
	director_id = fields.Many2one(
		'res.users', string='Ban lãnh đạo',
		compute='_compute_director_id', store=True
	)

	@api.depends('trp_approve_history_ids', 'trp_approve_history_ids.approve_user_id',
				 'trp_approve_history_ids.trp_approve_config_line_id')
	def _compute_director_id(self):
		for rec in self:
			default_user_id = self.env['ir.config_parameter'].sudo().get_param('biz_detailed_book_of_materials.unit_heads_id')
			try:
				default_user_id = int(default_user_id) if default_user_id else False
			except ValueError:
				default_user_id = False
				
			histories_with_level = rec.trp_approve_history_ids.filtered(
				lambda h: h.trp_approve_config_line_id and h.trp_approve_config_line_id.level
			)
			if histories_with_level:
				max_level = max(histories_with_level.mapped('trp_approve_config_line_id.level'))
				last_level_history = histories_with_level.filtered(
					lambda h: h.trp_approve_config_line_id.level == max_level and h.approve_user_id
				)
				if last_level_history:
					rec.director_id = last_level_history[0].approve_user_id
				else:
					rec.director_id = default_user_id
			else:
				rec.director_id = default_user_id

	# --- Trường dùng cho luồng duyệt trp.approve ---
	trp_approve_config_line_id = fields.Many2one(
		'trp.approve.config.line', string="Cấu hình duyệt", copy=False)
	delegate_approver_ids = fields.Many2many(
		'res.users', 'mrp_production_delegate_approve_rel', 'production_id', 'user_id',
		string="Người duyệt ủy quyền")
	current_approve_user_ids = fields.Many2many(
		'res.users', 'mrp_production_current_approve_users_rel', 'production_id', 'user_id',
		string="Người duyệt hiện tại",
		compute='_compute_current_approve_users')
	is_user_current = fields.Boolean(
		compute='_compute_is_user_current', string="Là người duyệt hiện tại",
		default=False, copy=False)
	approve_state_next = fields.Char('Trạng thái tiếp theo', default='approve')

	mrp_approval_state = fields.Selection([
		('draft', 'Nháp'),
		('waiting', 'Chờ duyệt'),
		('approved', 'Đã duyệt'),
		('refused', 'Từ chối'),
	], string='Trạng thái duyệt', default='draft', copy=False, tracking=True)

	trp_approve_history_ids = fields.One2many(
		'trp.approve.history', 'mrp_production_id',
		string='Lịch sử duyệt', copy=False)

	def _get_approvers_for_line(self, line):
		self.ensure_one()
		list_approver = []
		if line.user_ids:
			list_approver = line.user_ids.ids
		for j_line in line.job_ids:
			list_approver += j_line.employee_ids.ids

		if line.manager_type:
			field_map = {
				'voter': 'preparer_id',
				'supervisor': 'supervisor_id',
				'unit_heads': 'director_id',
				'receiver': 'user_id',
			}
			field_name = field_map.get(line.manager_type)
			if field_name and hasattr(self, field_name):
				user = getattr(self, field_name)
				if user and user.id not in list_approver:
					list_approver.append(user.id)
		return list_approver

	@api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.user_ids',
				 'trp_approve_config_line_id.job_ids', 'trp_approve_config_line_id.manager_type')
	def _compute_current_approve_users(self):
		for record in self:
			if record.trp_approve_config_line_id:
				approvers = record._get_approvers_for_line(record.trp_approve_config_line_id)
				record.current_approve_user_ids = [(6, 0, approvers)]
			else:
				record.current_approve_user_ids = False

	def _compute_is_user_current(self):
		for record in self:
			if record.trp_approve_config_line_id and record.current_approve_user_ids:
				record.is_user_current = self.env.user.id in record.current_approve_user_ids.ids
			else:
				record.is_user_current = False

	def action_send_approve(self):
		"""Gửi phê duyệt - tìm config và tạo history"""
		for rec in self:
			today = fields.Date.today()
			res_approve = self.env['trp.approve.config'].search(
				[('res_model', '=', self._name),
				 ('date_effective', '<=', today),
				 '|', ('date_expiration', '=', None),
				      ('date_expiration', '>=', today)],
				order='date_effective desc, id desc', limit=1)
			if not res_approve or not res_approve.trp_approve_config_line_ids:
				raise models.UserError(_('Không tìm thấy cấu hình duyệt cho Lệnh sản xuất!'))
			first_line = False
			for line in res_approve.trp_approve_config_line_ids:
				if rec._get_approvers_for_line(line):
					first_line = line
					break

			if not first_line:
				# Nếu không có bước nào có người duyệt, tự động duyệt luôn
				rec.write({'mrp_approval_state': 'approved'})
				continue

			res_new = self.env['trp.approve.history'].create({
				'trp_approve_config_line_id': first_line.id,
				'mrp_production_id': rec.id,
				'res_model': self._name,
				'res_id': rec.id,
				'user_id': self.env.user.id,
				'date': datetime.now(),
				'type': 'new',
			})
			rec.write({
				'trp_approve_config_line_id': first_line.id,
				'delegate_approver_ids': [(6, 0, first_line.delegate_approver_ids.ids)],
				'mrp_approval_state': 'waiting',
			})
			# Tạo activity thông báo cho người duyệt
			if rec.current_approve_user_ids:
				todo_act = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)
				res_model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
				for uid in rec.current_approve_user_ids.ids:
					self.env['mail.activity'].create({
						'activity_type_id': todo_act.id or False,
						'date_deadline': fields.Date.today(),
						'user_id': uid,
						'res_id': rec.id,
						'res_model': self._name,
						'res_model_id': res_model_id.id,
						'trp_approve_history_id': res_new.id,
					})

	def action_confirm_approve(self):
		"""Người duyệt bấm Duyệt"""
		for rec in self.sudo():
			res_history = self.env['trp.approve.history'].search(
				[('mrp_production_id', '=', rec.id),
				 ('trp_approve_config_line_id', '=', rec.trp_approve_config_line_id.id)],
				order='id desc', limit=1)
			if res_history:
				res_history.write({
					'approve_user_id': self.env.user.id,
					'approve_date': datetime.now(),
				})
				self.env['mail.activity'].search(
					[('trp_approve_history_id', '=', res_history.id)]
				).with_context(skip_approve_done=True).action_done()
			# Tìm bước duyệt tiếp theo
			today = fields.Date.today()
			res_approve = self.env['trp.approve.config'].search(
				[('res_model', '=', self._name),
				 ('date_effective', '<=', today),
				 '|', ('date_expiration', '=', None),
				      ('date_expiration', '>=', today)],
				order='date_effective desc, id desc', limit=1)
			config_lines = res_approve.trp_approve_config_line_ids
			next_line = False
			found_current = False
			for line in config_lines:
				if found_current:
					if rec._get_approvers_for_line(line):
						next_line = line
						break
				if line == rec.trp_approve_config_line_id:
					found_current = True
			if next_line:
				# Còn bước duyệt tiếp
				res_new = self.env['trp.approve.history'].create({
					'trp_approve_config_line_id': next_line.id,
					'mrp_production_id': rec.id,
					'res_model': self._name,
					'res_id': rec.id,
					'user_id': self.env.user.id,
					'date': datetime.now(),
					'type': 'new',
				})
				rec.write({'trp_approve_config_line_id': next_line.id})
				if rec.current_approve_user_ids:
					todo_act = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)
					res_model_id = self.env['ir.model'].search([('model', '=', self._name)], limit=1)
					for uid in rec.current_approve_user_ids.ids:
						self.env['mail.activity'].create({
							'activity_type_id': todo_act.id or False,
							'date_deadline': fields.Date.today(),
							'user_id': uid,
							'res_id': rec.id,
							'res_model': self._name,
							'res_model_id': res_model_id.id,
							'trp_approve_history_id': res_new.id,
						})
			else:
				# Hết bước → Hoàn thành
				rec.write({
					'trp_approve_config_line_id': False,
					'mrp_approval_state': 'approved',
				})

	def action_refuse(self):
		"""Từ chối phê duyệt"""
		for rec in self.sudo():
			res_histories = rec.trp_approve_history_ids
			self.env['mail.activity'].search(
				[('trp_approve_history_id', 'in', res_histories.ids)]
			).with_context(skip_approve_done=True).action_done()
			rec.write({
				'trp_approve_config_line_id': False,
				'mrp_approval_state': 'refused',
			})

	def action_reset_approve(self):
		"""Reset về Nháp"""
		self.write({
			'trp_approve_config_line_id': False,
			'mrp_approval_state': 'draft',
		})

	def action_cancel_approve(self):
		"""Huỷ duyệt (Dành cho Admin)"""
		for rec in self.sudo():
			res_histories = rec.trp_approve_history_ids
			self.env['mail.activity'].search(
				[('trp_approve_history_id', 'in', res_histories.ids)]
			).with_context(skip_approve_done=True).action_done()
			rec.write({
				'trp_approve_config_line_id': False,
				'mrp_approval_state': 'draft',
			})