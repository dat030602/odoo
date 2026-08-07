"""
Connector Code Execution Log
============================
Audit log model that records every code execution for traceability and debugging.
"""

from odoo import models, fields


class ConnectorCodeExecutionLog(models.Model):
    """Audit log for every code execution via connector.code.mixin.

    Records the model, record, user, code snapshot, result summary, and any
    errors that occurred during execution. This provides full traceability
    for debugging and security auditing.
    """

    _name = "connector.code.execution.log"
    _description = "Audit log for connector code execution"
    _order = "create_date desc"

    res_model = fields.Char(
        string="Model",
        required=True,
        help="The model name where the code was executed.",
    )
    res_id = fields.Integer(
        string="Record ID",
        required=True,
        help="The ID of the record where the code was executed.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        help="The user who triggered the code execution.",
    )
    code_snapshot = fields.Text(
        string="Code Snapshot",
        help="A copy of the Python code that was executed.",
    )
    state = fields.Selection(
        [("success", "Success"), ("error", "Error")],
        string="State",
        help="Whether the code execution succeeded or failed.",
    )
    result_summary = fields.Text(
        string="Result Summary",
        help="A truncated summary of the result returned by the code.",
    )
    error_message = fields.Text(
        string="Error Message",
        help="The error message if the code execution failed.",
    )
