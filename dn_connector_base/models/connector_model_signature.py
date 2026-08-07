"""
Connector Model Signature
=========================
Defines how to discover schema from raw JSON responses. Supports both
default discovery (automatic) and custom discovery (via Python code).
"""

import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ConnectorModelSignature(models.Model):
    """Defines schema discovery rules for a target model from raw JSON.

    Each signature is associated with an endpoint and defines the target
    model name, parent signature (for nested models), JSON path key, and
    whether to use custom discovery code.
    """

    _name = "connector.model.signature"
    _description = "Schema discovery definition for a target model"
    _inherit = ["connector.code.mixin"]

    endpoint_id = fields.Many2one(
        "connector.endpoint",
        string="Endpoint",
        ondelete="cascade",
        help="The endpoint this signature belongs to.",
    )
    target_model_name = fields.Char(
        string="Target Model Name",
        required=True,
        help="The Odoo model name to create (e.g., x_shopify_order). "
        "Must start with 'x_', use lowercase and underscores only, no dots.",
    )
    parent_signature_id = fields.Many2one(
        "connector.model.signature",
        string="Parent Signature",
        help="The parent signature if this is a nested model.",
    )
    json_path_key = fields.Char(
        string="JSON Path Key",
        help="Fixed JSON path key to identify this model (e.g., 'lines' or 'lines.taxes'). "
        "Used for stable model naming across sync runs.",
    )
    use_custom_discovery = fields.Boolean(
        string="Use Custom Discovery",
        help="If enabled, use Python code for schema discovery instead of the default algorithm.",
    )

    @api.constrains("target_model_name")
    def _check_model_name(self):
        """Validate that the target model name follows naming conventions.

        Ensures the model name starts with 'x_', contains only lowercase
        letters, digits, and underscores, and does not contain dots.

        :raises ValidationError: If the model name violates any naming rule.
        """
        for rec in self:
            name = rec.target_model_name or ""
            if not name.startswith("x_"):
                raise ValidationError(
                    _("Model name must start with 'x_'")
                )
            if "." in name:
                raise ValidationError(
                    _("Model name must not contain dots")
                )
            if not re.match(r"^[a-z0-9_]+$", name):
                raise ValidationError(
                    _("Model name must contain only lowercase letters, digits, and underscores")
                )

    def discover_schema(self, raw_json):
        """Discover the schema from a raw JSON response.

        If use_custom_discovery is enabled, executes the custom code.
        Otherwise, uses the default discovery algorithm.

        :param raw_json: The raw JSON response (as a dict) to discover schema from.
        :return: A dict with keys 'models', 'fields', and 'relations'.
        """
        if self.use_custom_discovery:
            return self.execute_code(extra_context={
                "raw_json": raw_json,
                "target_model": self.target_model_name,
            })
        return self._default_discover_schema(raw_json)

    def _default_discover_schema(self, raw_json):
        """Run the default schema discovery algorithm on raw JSON.

        Walks the JSON structure and identifies models (from arrays),
        fields (from primitives and objects), and relations (parent-child).

        :param raw_json: The raw JSON response (as a dict).
        :return: A dict with 'models', 'fields', and 'relations' lists.
        """
        discovered = {"models": [], "fields": [], "relations": []}
        self._walk_json(raw_json, self.target_model_name, discovered)
        return discovered

    def _walk_json(self, node, current_model, discovered, path_key=""):
        """Recursively walk a JSON node to discover schema elements.

        - Arrays trigger creation of child models with stable names based on
          the JSON path key (not traversal order).
        - Objects (dicts) are stored as Text fields (no model creation).
        - Primitives are always stored as Text fields.

        :param node: The current JSON node being processed.
        :param current_model: The model name for the current level.
        :param discovered: The accumulator dict for discovered schema.
        :param path_key: The dot-separated JSON path to the current node.
        """
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            field_name = f"x_{key}"
            if isinstance(value, list):
                child_path_key = f"{path_key}.{key}" if path_key else key
                child_model = self._resolve_or_create_model_name(
                    current_model, child_path_key
                )
                discovered["models"].append({
                    "name": child_model,
                    "json_path_key": child_path_key,
                    "parent": current_model,
                })
                discovered["relations"].append({
                    "parent": current_model,
                    "child": child_model,
                    "type": "one2many",
                })
                if value and isinstance(value[0], dict):
                    self._walk_json(value[0], child_model, discovered, child_path_key)
            elif isinstance(value, dict):
                discovered["fields"].append({
                    "model": current_model,
                    "name": field_name,
                    "type": "text",
                })
            else:
                discovered["fields"].append({
                    "model": current_model,
                    "name": field_name,
                    "type": "text",
                })

    def _resolve_or_create_model_name(self, parent_model, json_path_key):
        """Resolve or create a stable model name for a child model.

        Uses a mapping of json_path_key to model name to ensure stability
        across sync runs. If no mapping exists, generates a new name.

        :param parent_model: The parent model name.
        :param json_path_key: The fixed JSON path key for this child.
        :return: The model name for the child model.
        """
        mapping = self.env["connector.model.mapping"].search([
            ("parent_signature_id", "=", self.id),
            ("json_path_key", "=", json_path_key),
        ], limit=1)
        if mapping:
            return mapping.child_model_name
        index = len(self.env["connector.model.mapping"].search([
            ("parent_signature_id", "=", self.id),
        ])) + 1
        child_model = f"{parent_model}_{index}"
        self.env["connector.model.mapping"].create({
            "parent_signature_id": self.id,
            "json_path_key": json_path_key,
            "child_model_name": child_model,
        })
        return child_model

    def _get_child_signature(self, json_path_key):
        """Find the child signature for a given JSON path key.

        :param json_path_key: The JSON path key to look up.
        :return: The matching child signature record, or None.
        """
        return self.env["connector.model.signature"].search([
            ("parent_signature_id", "=", self.id),
            ("json_path_key", "=", json_path_key),
        ], limit=1)
