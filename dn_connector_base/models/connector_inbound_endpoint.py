# -*- coding: utf-8 -*-
import uuid
from odoo import models, fields, api, _

class ConnectorInboundEndpoint(models.Model):
    """Inbound Gateway Endpoint configuration for receiving webhooks and API calls."""

    _name = "connector.inbound.endpoint"
    _description = "Connector Inbound Endpoint"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(string="Name", required=True, tracking=True)
    framework_id = fields.Many2one(
        "connector.framework",
        string="Framework Preset",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    token = fields.Char(
        string="Token",
        required=True,
        default=lambda self: str(uuid.uuid4()),
        copy=False,
        index=True,
    )
    endpoint_url = fields.Char(
        string="Endpoint URL",
        compute="_compute_endpoint_url",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("paused", "Paused (Temporarily Disables Ingestion)"),
        ],
        string="State",
        required=True,
        default="active",
        tracking=True,
        index=True,
    )
    allowed_methods = fields.Selection(
        [
            ("POST", "POST Only"),
            ("POST_PUT", "POST & PUT"),
            ("ALL", "All (GET, POST, PUT, PATCH)"),
        ],
        string="Allowed Methods",
        required=True,
        default="POST",
    )
    ip_allowlist = fields.Text(string="IP Allowlist")
    secret = fields.Char(string="Secret", groups="base.group_system")
    auth_override = fields.Selection(
        [
            ("inherit", "Inherit Framework Auth"),
            ("none", "Public / None"),
            ("static_token", "Static Token"),
            ("hmac", "HMAC Signature"),
        ],
        string="Auth Override",
        required=True,
        default="inherit",
    )
    execution_mode = fields.Selection(
        [
            ("inherit", "Inherit Framework Mode"),
            ("immediate", "Immediate (Sync)"),
            ("deferred", "Deferred (Async Inbox)"),
        ],
        string="Execution Mode",
        required=True,
        default="inherit",
    )
    priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Urgent"),
        ],
        string="Priority",
        required=True,
        default="1",
    )
    ordering_key = fields.Selection(
        [
            ("none", "Parallel Processing"),
            ("entity_id", "Sequential by Entity ID"),
            ("event_type", "Sequential by Event Type"),
        ],
        string="Ordering Key",
        required=True,
        default="none",
    )
    ordering_json_path = fields.Char(string="Ordering JSON Path", default="id")
    response_mode = fields.Selection(
        [
            ("ack", "Fast Acknowledgment JSON"),
            ("handler_result", "Handler Result"),
        ],
        string="Response Mode",
        required=True,
        default="ack",
    )
    sync_timeout_s = fields.Integer(string="Sync Timeout (s)", default=30)
    fallback_status = fields.Integer(string="Fallback Status", default=200)
    handler_type = fields.Selection(
        [
            ("store_only", "Store Only (Inbox Archive)"),
            ("raw_model", "Raw Model (Auto Schema x_*)"),
            ("server_action", "Server Action (ir.actions.server)"),
            ("python", "Python Safe Eval Code"),
            ("pack", "Connector Pack Handler"),
        ],
        string="Handler Type",
        required=True,
        default="python",
    )
    target_model_id = fields.Many2one("ir.model", string="Target Model")
    target_model_name = fields.Char(
        string="Target Model Name",
        related="target_model_id.model",
        readonly=True,
    )
    server_action_id = fields.Many2one("ir.actions.server", string="Server Action")
    pack_handler_id = fields.Char(string="Pack Handler ID")
    code = fields.Text(string="Python Code", groups="dn_connector_base.group_connector_developer")
    max_backlog = fields.Integer(string="Max Backlog", default=10000)
    retention_days = fields.Integer(string="Retention Days (0 = system default)", default=0)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    message_ids = fields.One2many(
        "connector.inbound.message",
        "endpoint_id",
        string="Messages",
        domain=[],
    )
    message_count = fields.Integer(
        string="Message Count",
        compute="_compute_message_count",
    )
    dead_letter_count = fields.Integer(
        string="Dead Letter Count",
        compute="_compute_message_count",
    )

    _uniq_endpoint_token = models.Constraint(
        "unique(token)",
        "Endpoint token must be globally unique!",
    )

    def _compute_endpoint_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")  # sudo: read base web url system parameter
        for record in self:
            record.endpoint_url = f"{base_url.rstrip('/')}/connector/in/{record.token}" if record.token else False

    def _compute_message_count(self):
        msg_data = self.env["connector.inbound.message"]._read_group(
            [("endpoint_id", "in", self.ids)],
            ["endpoint_id"],
            ["__count"],
        )
        counts = {ep.id: count for ep, count in msg_data}
        dead_data = self.env["connector.inbound.message"]._read_group(
            [("endpoint_id", "in", self.ids), ("state", "=", "dead")],
            ["endpoint_id"],
            ["__count"],
        )
        dead_counts = {ep.id: count for ep, count in dead_data}
        for record in self:
            record.message_count = counts.get(record.id, 0)
            record.dead_letter_count = dead_counts.get(record.id, 0)

    def action_view_messages(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Inbox Messages"),
            "res_model": "connector.inbound.message",
            "view_mode": "list,form",
            "domain": [("endpoint_id", "=", self.id)],
            "context": {"default_endpoint_id": self.id},
        }

    def action_view_dead_letters(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Dead Letter Queue"),
            "res_model": "connector.inbound.message",
            "view_mode": "list,form",
            "domain": [("endpoint_id", "=", self.id), ("state", "=", "dead")],
            "context": {"default_endpoint_id": self.id},
        }
