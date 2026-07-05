from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ApprovalReasonWizard(models.TransientModel):
    _name = 'approval.reason.wizard'
    _description = 'Approval Reason Wizard'

    reason = fields.Char(string='Reason', required=True)
    request_id = fields.Many2one('approval.request', string='Approval Request', required=True)
    action_type = fields.Selection([
        ('reject', 'Reject'),
        ('cancel', 'Cancel'),
    ], string='Action Type', required=True)

    def action_confirm(self):
        self.ensure_one()
        request = self.request_id
        
        if self.action_type == 'reject':
            # Cancel pending activities for current user with feedback
            request._custom_cancel_activities(user=self.env.user, feedback=self.reason)
            request.write({"custom_request_status": "refused"})
            # Update existing pending history to refused
            request._update_approval_history('refused', self.env.user)
        elif self.action_type == 'cancel':
            # Cancel pending activities for current user with feedback
            request._custom_cancel_activities(user=self.env.user, feedback=self.reason)
            request.write({"custom_request_status": "cancel"})
            # Update existing pending history to cancel status
            request._update_approval_history('cancel', self.env.user)
        
        return {'type': 'ir.actions.act_window_close'}
