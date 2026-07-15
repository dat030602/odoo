# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TrpApproveHistory(models.Model):
	_name = 'trp.approve.history'

	name = fields.Char(string="Tên")
	type = fields.Selection([('new', 'Mới'), ('cancel', 'Hủy')], string="Phân loại")
	res_model = fields.Char(string="Mô hình")
	res_id = fields.Integer(string="Id liên quan")
	user_id = fields.Many2one('res.users', "Người yêu cầu")
	date = fields.Datetime(string="Ngày yêu cầu")
	approve_user_id = fields.Many2one('res.users', "Người duyệt")
	approve_date = fields.Datetime(string="Ngày duyệt")
	trp_approve_config_line_id = fields.Many2one('trp.approve.config.line', string="Chi tiết phê duyệt")
	manager_type = fields.Selection(string='Loại quản lý', related="trp_approve_config_line_id.manager_type")
	user_ids = fields.Many2many('res.users', string="Người duyệt", related="trp_approve_config_line_id.user_ids")
	delegate_approver_ids = fields.Many2many('res.users', 'delegate_approve_history_users_rel', string="Người duyệt được ủy quyền")
	approve_user_ids = fields.Many2many('res.users', 'approve_users_rel', string="Người duyệt", compute='_compute_approve_user_ids')
	job_ids = fields.Many2many('hr.job', string="Chức Vụ Duyệt", related="trp_approve_config_line_id.job_ids")
	reason_id = fields.Many2one("trp.approve.reason", string="Lý do")
	reason = fields.Text(string="Lý do từ chối")
	internal_account_id = fields.Many2one('alpha.internal.account', string="Alpha account")
	allow_sign = fields.Integer(string="Ký nháy", related="trp_approve_config_line_id.allow_sign")
	sign_requests_id = fields.Many2one('sign.requests', string="Sign Requests", ondelete='cascade')
	all_approved_user_ids = fields.Many2many('res.users', 'history_all_approved_users_rel', 'history_id', 'user_id', string="Đã duyệt (chế độ tất cả)")

	@api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type', 'trp_approve_config_line_id.user_ids', \
		'trp_approve_config_line_id.job_ids')
	def _compute_approve_user_ids(self):
		for record in self:
			list_approver = []
			if record.trp_approve_config_line_id:
				if record.trp_approve_config_line_id.user_ids:
					list_approver = record.trp_approve_config_line_id.user_ids.ids

				for line in record.trp_approve_config_line_id.job_ids:
					list_approver += line.employee_ids.ids

				if record.trp_approve_config_line_id.manager_type:
					if record.trp_approve_config_line_id.manager_type == "manager":
						user_manager = record.create_uid.department_id.manager_id.user_id.id
						if user_manager:
							list_approver.append(user_manager)
					elif record.trp_approve_config_line_id.manager_type == "parent":
						user_parent = record.create_uid.employee_id.parent_id.user_id.id
						if user_parent:
							list_approver.append(user_parent)
					elif record.trp_approve_config_line_id.manager_type == "delegate":
						# Kiem tra co field payment_request_id thi lay
						if hasattr(record, 'payment_request_id') and record.payment_request_id:
							approved_user_ids = record.payment_request_id.trp_approve_history_ids.mapped('approve_user_id')
						elif hasattr(record, 'sign_requests_id') and record.sign_requests_id:
							approved_user_ids = record.sign_requests_id.trp_approve_history_ids.mapped('approve_user_id')
						elif hasattr(record, 'sale_sign_requests_id') and record.sale_sign_requests_id:
							approved_user_ids = record.sale_sign_requests_id.trp_approve_history_ids.mapped('approve_user_id')
						elif hasattr(record, 'purchase_sign_requests_id') and record.purchase_sign_requests_id:
							approved_user_ids = record.purchase_sign_requests_id.trp_approve_history_ids.mapped('approve_user_id')
						else:
							approved_user_ids = record.internal_account_id.trp_approve_history_ids.mapped('approve_user_id')
						list_approver += (record.trp_approve_config_line_id.delegate_approver_ids - approved_user_ids)[0].ids
				record.approve_user_ids = [(6,0,list_approver)]
			else:
				record.approve_user_ids = False
