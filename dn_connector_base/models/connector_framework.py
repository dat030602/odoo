# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ConnectorFramework(models.Model):
    """Represents an external system framework preset with authentication
    and event routing configuration."""

    _name = "connector.framework"
    _description = "Connector Framework Preset"
    _order = "name"

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string="Code", required=True, index=True)
    auth_type = fields.Selection(
        [
            ("none", "No Authentication"),
            ("static_token", "Static Token / Bearer"),
            ("basic", "HTTP Basic Auth"),
            ("hmac", "HMAC Cryptographic Signature"),
        ],
        string="Auth Type",
        required=True,
        default="none",
    )
    auth_header = fields.Char(string="Auth Header", default="Authorization")
    hmac_algo = fields.Selection(
        [
            ("sha256", "HMAC-SHA256"),
            ("sha1", "HMAC-SHA1"),
            ("sha512", "HMAC-SHA512"),
        ],
        string="HMAC Algorithm",
        default="sha256",
    )
    hmac_encoding = fields.Selection(
        [
            ("hex", "Hexadecimal (Lowercase)"),
            ("base64", "Base64 Encoded"),
        ],
        string="HMAC Encoding",
        default="hex",
    )
    hmac_prefix = fields.Char(string="HMAC Prefix")
    signature_template = fields.Char(string="Signature Template")
    event_type_header = fields.Char(string="Event Type Header")
    event_type_json_path = fields.Char(string="Event Type JSON Path")
    idempotency_header = fields.Char(string="Idempotency Header")
    idempotency_json_path = fields.Char(string="Idempotency JSON Path")
    default_execution_mode = fields.Selection(
        [
            ("immediate", "Immediate (Synchronous)"),
            ("deferred", "Deferred (Asynchronous Inbox)"),
        ],
        string="Default Execution Mode",
        required=True,
        default="deferred",
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    endpoint_ids = fields.One2many(
        "connector.inbound.endpoint",
        "framework_id",
        string="Endpoints",
    )
    endpoint_count = fields.Integer(
        string="Endpoint Count",
        compute="_compute_endpoint_count",
    )

    _uniq_framework_code = models.Constraint(
        "unique(code)",
        "Framework code must be unique!",
    )

    @api.depends("endpoint_ids")
    def _compute_endpoint_count(self):
        endpoint_data = self.env["connector.inbound.endpoint"]._read_group(
            [("framework_id", "in", self.ids)],
            ["framework_id"],
            ["__count"],
        )
        counts = {fw.id: count for fw, count in endpoint_data}
        for record in self:
            record.endpoint_count = counts.get(record.id, 0)

    def action_view_endpoints(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Endpoints"),
            "res_model": "connector.inbound.endpoint",
            "view_mode": "list,form",
            "domain": [("framework_id", "=", self.id)],
            "context": {"default_framework_id": self.id},
        }
