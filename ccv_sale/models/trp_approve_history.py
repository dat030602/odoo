# -*- coding: utf-8 -*-

from odoo import models, fields, api

class TrpApproveHistory(models.Model):
	_inherit = 'trp.approve.history'

	sale_sign_requests_id = fields.Many2one('sale.sign.requests', string="Sale Sign Requests", ondelete='cascade')

	@api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type', 'trp_approve_config_line_id.user_ids', \
		'trp_approve_config_line_id.job_ids', 'sale_sign_requests_id.current_approve_user_ids')
	def _compute_approve_user_ids(self):
		super(TrpApproveHistory, self)._compute_approve_user_ids()
		for record in self:
			list_approver = record.approve_user_ids
			if record.sale_sign_requests_id:
				list_approver |= record.sale_sign_requests_id.current_approve_user_ids
			record.approve_user_ids = [(6,0,list_approver.ids)]
