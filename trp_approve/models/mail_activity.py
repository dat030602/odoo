# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class MailActivity(models.Model):
	_inherit = 'mail.activity'

	trp_approve_history_id = fields.Many2one('trp.approve.history', string="Lịch sử phê duyệt")

	def _action_done(self, feedback=False, attachment_ids=False):
		"""Override action_done to trigger action_agree when activity is completed"""
		ctx = self.env.context
		if not ctx.get('skip_approve_done', False):
			for activity in self:
				history_id = activity.trp_approve_history_id
				if history_id:
					if 'sale_sign_requests_id' in history_id._fields and history_id.sale_sign_requests_id:
						if not history_id.sale_sign_requests_id.check_user():
							raise UserError("Người dùng không có quyền phê duyệt !!!")
						history_id.sale_sign_requests_id.action_agree()
					elif 'purchase_sign_requests_id' in history_id._fields and history_id.purchase_sign_requests_id:
						if not history_id.purchase_sign_requests_id.check_user():
							raise UserError("Người dùng không có quyền phê duyệt !!!")
						history_id.purchase_sign_requests_id.action_agree()
					elif history_id.internal_account_id:
						if not history_id.internal_account_id.check_user():
							raise UserError("Người dùng không có quyền phê duyệt !!!")
						history_id.internal_account_id.action_agree()
		messages, next_activities = super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)
		return messages, next_activities
