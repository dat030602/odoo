# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class TrpApprove(models.Model):
	_name = 'trp.approve.config'
	_description = "Cấu hình duyệt"

	name = fields.Char(string="Tên", required=True, default='/', readonly=True, copy=False)
	model_id = fields.Many2one('ir.model', 'Mô hình', ondelete='cascade')
	product_id = fields.Many2one('product.product', 'Sản phẩm')
	res_model = fields.Char(related="model_id.model", store=True)
	model_ids = fields.Many2many('ir.model')
	date_effective = fields.Date(string="Ngày hiệu lực", default=datetime.today())
	date_expiration = fields.Date(string="Ngày hết hạn")
	trp_approve_config_line_ids = fields.One2many('trp.approve.config.line', 'trp_approve_config_id', string="Quy tắc duyệt")
	is_applied = fields.Boolean(string="Đã áp dụng", compute='_compute_is_applied', store=True)
	account_id = fields.Many2one(string="Từ tài khoản", comodel_name='account.account',
								 help="Account to transfer to.")
	destination_account_id = fields.Many2one(string="Đến tài khoản", comodel_name='account.account',
											 help="Account to transfer to.")
	journal_id = fields.Many2one('account.journal', string="Sổ nhật ký",
								 domain="[('company_id', '=', company_id)]",
								 help="Journal where to create the entry.")
	company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
	@api.depends('trp_approve_config_line_ids', 'trp_approve_config_line_ids.is_applied')
	def _compute_is_applied(self):
		for record in self:
			if any(l.is_applied for l in record.trp_approve_config_line_ids):
				record.is_applied = True
			else:
				record.is_applied = False

	@api.onchange('name')
	def onchange_name(self):
		self.model_ids = False
		model_fields_ids = self.env['ir.model.fields'].search([('name', '=', 'trp_approve_config_line_id'), ('model', 'not in', ('trp.approve.config.reason', 'trp.approve.history', 'trp.approve'))])
		if model_fields_ids:
			list_name_model = model_fields_ids.mapped('model')
			model_ids = self.env['ir.model'].search([('model', 'in', list_name_model)])
			if model_ids:
				self.model_ids = model_ids.mapped('id')

	@api.model
	def create(self, vals):
		if vals.get('name', '/') == '/':
			seq_date = None
			vals['name'] = self.env['ir.sequence'].next_by_code('trp.approve.config', sequence_date=seq_date) or '/'
		res = super(TrpApprove, self).create(vals)
		return res
	
	def unlink(self):
		if any(rec.is_applied for rec in self):
			raise ValidationError(_("Bạn không thể xóa cấu hình đã có phát sinh. Hãy lưu trữ thay vì xóa."))
		return super(TrpApprove, self).unlink()
