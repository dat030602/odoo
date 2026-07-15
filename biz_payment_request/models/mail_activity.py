# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class MailActivity(models.Model):
	_inherit = 'mail.activity'

	def _action_done(self, feedback=False, attachment_ids=False):
		"""Override action_done to trigger action_agree when activity is completed"""
		ctx = self.env.context
		if not ctx.get('skip_approve_done', False):
			for activity in self:
				if activity.trp_approve_history_id and activity.trp_approve_history_id.payment_request_id:
					if not activity.trp_approve_history_id.payment_request_id.check_user():
						raise UserError("Người dùng không có quyền phê duyệt !!!")
					activity.trp_approve_history_id.payment_request_id.action_agree()

		messages, activities = super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)
		return messages, activities
