from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class ApprovalWorkflowStage(models.Model):
    _name = "approval.workflow.stage"
    _description = "Approval Workflow Stage"
    _order = "workflow_id, sequence, id"

    workflow_id = fields.Many2one("approval.workflow.config", string="Workflow", required=True, ondelete="cascade")
    name = fields.Char(string="Stage Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    approver_type = fields.Selection(
        [
            ("user", "Specific User"),
            ("group", "User Group"),
        ],
        string="Approver Type",
        required=True,
        default="user",
    )
    user_id = fields.Many2one("res.users", string="Approver User")
    group_id = fields.Many2one("res.groups", string="Approver Group")
    condition_python = fields.Text(string="Python Condition", help="Python code that returns True/False. Example: result = self.amount_total > 10000")
    parent_id = fields.Many2one("approval.workflow.stage", string="Parent Stage", ondelete="cascade")
    child_ids = fields.One2many("approval.workflow.stage", "parent_id", string="Child Stages")

    @api.constrains("parent_id")
    def _check_parent_id(self):
        for rec in self:
            if not rec.parent_id:
                continue
            # Check if parent_id would create a cyclic reference
            parent = rec.parent_id
            while parent:
                if parent.id == rec.id:
                    raise ValidationError(_("You cannot create cyclic hierarchy."))
                parent = parent.parent_id

    def evaluate_condition(self, record):
        """
        Evaluate the Python condition for this stage against a record.
        Returns True if condition passes or if no condition is defined.
        """
        self.ensure_one()
        if not self.condition_python:
            return True

        try:
            local_dict = {"self": record, "result": True}
            exec(self.condition_python, {}, local_dict)
            return bool(local_dict.get("result", True))
        except Exception as e:
            raise UserError(_("Error evaluating condition for stage '%s': %s") % (self.name, str(e)))

    def get_approvers(self):
        """
        Get the list of approvers for this stage based on approver_type.
        Returns a recordset of res.users.
        """
        self.ensure_one()
        if self.approver_type == "user" and self.user_id:
            return self.user_id
        elif self.approver_type == "group" and self.group_id:
            return self.group_id.user_ids
        return self.env["res.users"]

    def get_next_stages(self, record=None):
        """
        Get the next stages in the hierarchy based on traversal order.
        If record is provided, only return stages where condition evaluates to True.
        Returns a recordset of approval.workflow.stage ordered by hierarchy traversal.
        """
        self.ensure_one()

        # Get child stages in sequence order
        child_stages = self.child_ids.sorted("sequence")
        if not record:
            return child_stages
        # Filter by condition if record is provided
        valid_stages = self.env["approval.workflow.stage"]
        for stage in child_stages:
            if stage.evaluate_condition(record):
                valid_stages |= stage
                # If multiple stages at same level have condition = true, take the first one
                break
        return valid_stages

    @api.model
    def get_root_stages(self, workflow_id, record=None):
        """
        Get the root stages (stages without parent) for a workflow.
        If record is provided, only return stages where condition evaluates to True.
        """
        root_stages = self.search([
            ("workflow_id", "=", workflow_id),
            ("parent_id", "=", False)
        ], order="sequence, id")

        if not record:
            return root_stages

        # Filter by condition if record is provided
        valid_stages = self.env["approval.workflow.stage"]
        for stage in root_stages:
            if stage.evaluate_condition(record):
                valid_stages |= stage
                # If multiple stages at same level have condition = true, take the first one
                break

        return valid_stages
