"""
Connector Model Mapping
=======================
Stores the mapping between JSON path keys and generated model names
to ensure stable model naming across sync runs.
"""

from odoo import models, fields


class ConnectorModelMapping(models.Model):
    """Maps JSON path keys to generated child model names.

    This ensures that child models are named consistently across sync runs,
    preventing schema drift when the API changes field ordering.
    """

    _name = "connector.model.mapping"
    _description = "Mapping of JSON path keys to model names"

    parent_signature_id = fields.Many2one(
        "connector.model.signature",
        string="Parent Signature",
        required=True,
        ondelete="cascade",
        help="The parent model signature.",
    )
    json_path_key = fields.Char(
        string="JSON Path Key",
        required=True,
        help="The fixed JSON path key (e.g., 'lines', 'lines.taxes').",
    )
    child_model_name = fields.Char(
        string="Child Model Name",
        required=True,
        help="The generated Odoo model name for this child.",
    )

    _sql_constraints = [
        (
            "parent_json_path_unique",
            "unique(parent_signature_id, json_path_key)",
            "Each JSON path key must be unique per parent signature.",
        ),
    ]
