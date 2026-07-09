from odoo import _, api, fields, models
from odoo.exceptions import UserError
import markupsafe


class ApprovalHistory(models.Model):
    _name = "approval.history"
    _description = "Approval History"
    _order = "create_date"
    
    name = fields.Char(string="Reference", compute="_compute_name", store=True)
    request_id = fields.Many2one("approval.request", string="Approval Request", required=True, ondelete="cascade")
    workflow_id = fields.Many2one("approval.workflow.config", string="Workflow Configuration", related="request_id.workflow_id", store=True)
    stage_id = fields.Many2one("approval.workflow.stage", string="Stage", store=True)
    
    # Approval status
    status = fields.Selection([
        ('new', 'New'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancelled'),
    ], string="Approval Status", default='new', required=True)
    
    # User information
    approver_id = fields.Many2one("res.users", string="Approver", help="User who clicked the approval button")
    eligible_approvers_ids = fields.Many2many("res.users", string="Eligible Approvers", 
                                               help="List of users who can approve at this time")
    
    # Time tracking
    approval_time = fields.Datetime(string="Approval Time", help="Time when approver clicked the button")
    sent_time = fields.Datetime(string="Sent Time", help="Time when the request was sent")
    
    # Additional information
    comments = fields.Text(string="Comments")
    company_id = fields.Many2one("res.company", string="Company", related="request_id.company_id", store=True)
    
    @api.depends("request_id", "create_date")
    def _compute_name(self):
        for rec in self:
            rec.name = markupsafe.Markup(f"{rec.request_id.name if rec.request_id else 'N/A'} - {rec.create_date.strftime('%Y-%m-%d %H:%M:%S') if rec.create_date else 'N/A'}")
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            # Post message to approval request
            if rec.request_id:
                message_body = self._get_history_message(rec)
                rec.request_id.message_post(body=markupsafe.Markup(message_body))
        return records
    
    def _get_history_message(self, history):
        """Generate message body for approval history"""
        if history.status == 'new':
            return markupsafe.Markup(_("<b>Approval Request Created</b><br/>Sent: %s") % (history.sent_time.strftime('%Y-%m-%d %H:%M:%S') if history.sent_time else 'N/A'))
        elif history.status == 'pending':
            return markupsafe.Markup(_("<b>Approval Request Sent</b><br/>Sent: %s<br/>Eligible Approvers: %s") % (
                history.sent_time.strftime('%Y-%m-%d %H:%M:%S') if history.sent_time else 'N/A',
                ', '.join(history.eligible_approvers_ids.mapped('name'))
            ))
        elif history.status == 'approved':
            return markupsafe.Markup(_("<b>Approved</b><br/>Approver: %s<br/>Approval Time: %s") % (
                history.approver_id.name if history.approver_id else 'N/A',
                history.approval_time.strftime('%Y-%m-%d %H:%M:%S') if history.approval_time else 'N/A'
            ))
        elif history.status == 'refused':
            return markupsafe.Markup(_("<b>Refused</b><br/>Approver: %s<br/>Refusal Time: %s") % (
                history.approver_id.name if history.approver_id else 'N/A',
                history.approval_time.strftime('%Y-%m-%d %H:%M:%S') if history.approval_time else 'N/A'
            ))
        elif history.status == 'cancel':
            return markupsafe.Markup(_("<b>Cancelled</b><br/>Cancelled by: %s<br/>Cancellation Time: %s") % (
                history.approver_id.name if history.approver_id else 'N/A',
                history.approval_time.strftime('%Y-%m-%d %H:%M:%S') if history.approval_time else 'N/A'
            ))
        return markupsafe.Markup(_("Approval Status Updated: %s") % history.status)
