from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError, ValidationError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    workflow_id = fields.Many2one("approval.workflow.config", string="Workflow Configuration")
    current_stage_id = fields.Many2one("approval.workflow.stage", string="Current Stage", copy=False)
    can_click_approval = fields.Boolean(string="Can Click Approval Buttons", compute="_compute_can_click_approval")
    approval_history_ids = fields.One2many("approval.history", "request_id", string="Approval History")
    
    # Custom request_status field (non-computed) for custom views and buttons
    custom_request_status = fields.Selection([
        ('new', 'To Submit'),
        ('pending', 'Submitted'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Canceled'),
    ], default="new", string="Custom Request Status", tracking=True, copy=False)

    @api.depends("custom_request_status", "workflow_id", "current_stage_id")
    def _compute_can_click_approval(self):
        for rec in self:
            rec.can_click_approval = (
                rec.custom_request_status == "pending"
                and rec.workflow_id
                and rec.current_stage_id
                and self.env.user in rec.current_stage_id.get_approvers()
            )

    def action_custom_approve(self):
        for rec in self:
            if not rec.workflow_id:
                raise UserError(_("No workflow configured for this approval request."))

            current_stage = rec.current_stage_id
            if not current_stage:
                # Get first stage from hierarchy root
                Stage = self.env["approval.workflow.stage"]
                first_stage = Stage.get_root_stages(rec.workflow_id.id, record=rec)
                if first_stage:
                    rec.current_stage_id = first_stage.id
                    rec.custom_request_status = 'pending'
                    # Send activity notification to first stage approvers
                    rec._send_approval_notification(first_stage)
                    # Create approval history for pending status
                    eligible_approvers = first_stage.get_approvers()
                    rec._custom_create_approval_history('pending', None, eligible_approvers)
                else:
                    rec.write({"custom_request_status": "approved"})
                    # Update existing pending history to approved
                    rec._update_approval_history('approved', self.env.user)
                return

            next_stage = rec._get_next_stage(current_stage)
            rec._custom_done_activities(user=self.env.user)
            # Done activity current user
            rec._custom_cancel_activities()
            rec._update_approval_history('approved', self.env.user)
            if next_stage:
                rec.current_stage_id = next_stage.id
                rec.custom_request_status = 'pending'
                # Send activity notification to next stage approvers
                rec._send_approval_notification(next_stage)
                # Create approval history for pending status with next stage approvers
                eligible_approvers = next_stage.get_approvers()
                rec._custom_create_approval_history('pending', None, eligible_approvers)
            else:
                rec.write({"custom_request_status": "approved"})

    def action_custom_reject(self):
        self.ensure_one()
        return {
            'name': _('Reject Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_action_type': 'reject',
            }
        }

    def action_custom_cancel(self):
        self.ensure_one()
        return {
            'name': _('Cancel Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_action_type': 'cancel',
            }
        }

    def _get_next_stage(self, current_stage):
        """
        Get the next stage based on hierarchy traversal.
        Uses the workflow stage's hierarchy traversal logic:
        - If current_stage has children, get the first child where condition evaluates to True
        - If no children or no condition matches, return None (workflow complete)
        """
        self.ensure_one()
        next_stages = current_stage.get_next_stages(record=self)
        return next_stages[0] if next_stages else None

    def _send_approval_notification(self, stage):
        """
        Send activity notification to approvers of the given stage.
        """
        self.ensure_one()
        approvers = stage.get_approvers()
        if approvers:
            for approver in approvers:
                self.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=approver.id,
                    summary=_("Approval Request: %s") % self.name,
                    note=_("Please review and approve this request at stage: %s") % stage.name,
                )

    def _evaluate_condition(self, condition_python):
        self.ensure_one()
        local_dict = {"self": self, "result": False}
        try:
            exec(condition_python, local_dict)
            return local_dict.get("result", False)
        except Exception as e:
            raise UserError(_("Error evaluating condition: %s") % str(e))
    
    def _custom_cancel_activities(self, user=False, feedback=False):
        """
        Cancel all pending activities for the current user on this request.
        """
        self.ensure_one()
        domain = []
        if user:
            domain.append(('user_id', '=', user))
        domain.append(('state', '!=', 'done'))
        activities = self.activity_ids.filtered_domain(domain)
        if not feedback:
            activities.action_cancel()
        else:
            activities.action_feedback(feedback=feedback)

    def _custom_done_activities(self, user=False):
        """
        Mark all pending activities for the current user on this request as done.
        """
        self.ensure_one()
        domain = []
        if user:
            domain.append(('user_id', '=', user))
        domain.append(('state', '!=', 'done'))
        activities = self.activity_ids.filtered_domain(domain)
        activities.action_done()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.category_id and rec.category_id.workflow_config_id:
                rec.workflow_id = rec.category_id.workflow_config_id
            # Initialize custom_request_status to 'new' if not set
            if not rec.custom_request_status:
                rec.custom_request_status = 'new'
        return records
    
    def _custom_create_approval_history(self, status, approver=None, eligible_approvers=None):
        """
        Create an approval history record.
        
        Args:
            status: The approval status ('new', 'pending', 'approved', 'refused', 'cancel')
            approver: The user who approved/refused (for approved/refused/cancel status)
            eligible_approvers: List of users who can approve (for pending status)
        """
        self.ensure_one()
        
        vals = {
            'request_id': self.id,
            'status': status,
            'stage_id': self.current_stage_id.id if self.current_stage_id else None,
            'sent_time': fields.Datetime.now() if status in ['new', 'pending'] else None,
            'approval_time': fields.Datetime.now() if status in ['approved', 'refused', 'cancel'] else None,
        }
        
        if approver:
            vals['approver_id'] = approver.id
        
        if eligible_approvers:
            vals['eligible_approvers_ids'] = [(6, 0, eligible_approvers.ids)]
        
        self.env['approval.history'].create(vals)
    
    def _update_approval_history(self, status, approver):
        """
        Update the most recent pending approval history record to approved/refused/cancel status.
        
        Args:
            status: The new status ('approved', 'refused', 'cancel')
            approver: The user who approved/refused/cancelled
        """
        self.ensure_one()
        
        # Find the most recent pending history record for current stage
        pending_history = self.env['approval.history'].search([
            ('request_id', '=', self.id),
            ('status', '=', 'pending'),
            ('stage_id', '=', self.current_stage_id.id if self.current_stage_id else False),
        ], order='create_date desc', limit=1)
        
        if pending_history:
            # Update the existing pending record
            pending_history.write({
                'status': status,
                'approver_id': approver.id,
                'approval_time': fields.Datetime.now(),
            })
        else:
            # If no pending record exists, create a new one
            self._custom_create_approval_history(status, approver, None)

    def action_open_cancel_wizard(self):
        self.ensure_one()
        action = self.env.ref('dn_advanced_dynamic_approval.action_approval_reason_wizard').sudo().read()[0]
        action['context'] = {'default_approval_request_id': self.id, 'default_action': 'cancel'}
        return action

    def action_open_reject_wizard(self):
        self.ensure_one()
        action = self.env.ref('dn_advanced_dynamic_approval.action_approval_reason_wizard').sudo().read()[0]
        action['context'] = {'default_approval_request_id': self.id, 'default_action': 'reject'}
        return action

    def unlink(self):
        for rec in self:
            if rec.custom_request_status not in ['new', 'cancel'] and rec.workflow_id:
                raise UserError(_("You can only delete approval requests that are in 'To Submit' or 'Canceled' status."))
        return super().unlink()
