from odoo import fields, models


class ApprovalFieldConfig(models.Model):
    _name = "approval.field.config"
    _description = "Approval Field Configuration"
    _order = "workflow_id, field_id"

    workflow_id = fields.Many2one("approval.workflow.config", string="Workflow", required=True, ondelete="cascade")
    model_id = fields.Many2one("ir.model", string="Model", ondelete="cascade", related="workflow_id.model_id", store=True)
    field_id = fields.Many2one("ir.model.fields", string="Field", required=True, ondelete="cascade")
    readonly = fields.Boolean(string="Readonly", default=False)
    required = fields.Boolean(string="Required", default=False)
