from odoo import fields, models


class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    workflow_config_id = fields.Many2one(
        "approval.workflow.config",
        string="Workflow Configuration",
        help="Bind approval category with workflow configuration",
    )
