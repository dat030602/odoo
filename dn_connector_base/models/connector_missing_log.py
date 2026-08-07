"""
Connector Missing Log
=====================
Log model that records missing fields when Auto Create Schema is disabled.
"""

from odoo import models, fields


class ConnectorMissingLog(models.Model):
    """Log entry for missing fields when Auto Create Schema is disabled.

    When auto_create_schema is False and a field is encountered that does
    not exist on the target model, a missing log entry is created instead
    of raising an error. Fields are grouped by model to avoid duplicate logs.
    """

    _name = "connector.missing.log"
    _description = "Log for missing fields during import"
    _order = "create_date desc"

    endpoint_id = fields.Many2one(
        "connector.endpoint",
        string="Endpoint",
        required=True,
        ondelete="cascade",
        help="The endpoint where the missing field was encountered.",
    )
    model_name = fields.Char(
        string="Model",
        required=True,
        help="The Odoo model name where the field is missing.",
    )
    field_names = fields.Text(
        string="Missing Fields",
        required=True,
        help="Comma-separated list of missing field names.",
    )
