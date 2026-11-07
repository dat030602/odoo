# -*- coding: utf-8 -*-
import datetime
import json
import logging
import math
import random
import re
import sys
import traceback
import uuid

from odoo import models, fields, api, _
from odoo.tools import SQL
from .connector_code_mixin import _dynamic_import, _execute_safe_eval

_logger = logging.getLogger(__name__)


class ConnectorInboundMessage(models.Model):
    """Transactional inbox message record for incoming gateway webhooks/requests."""

    _name = "connector.inbound.message"
    _description = "Inbound Gateway Message (Inbox)"
    _order = "received_at desc, id desc"

    uuid = fields.Char(
        string="UUID",
        required=True,
        default=lambda self: str(uuid.uuid4()),
        copy=False,
        index=True,
    )
    endpoint_id = fields.Many2one(
        "connector.inbound.endpoint",
        string="Endpoint",
        required=True,
        ondelete="cascade",
        index=True,
    )
    framework_id = fields.Many2one(
        "connector.framework",
        string="Framework",
        related="endpoint_id.framework_id",
        store=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="endpoint_id.company_id",
        store=True,
        index=True,
    )
    received_at = fields.Datetime(
        string="Received At",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    remote_ip = fields.Char(string="Remote IP", index=True)
    method = fields.Char(string="HTTP Method", index=True)
    headers = fields.Json(string="Headers")
    body_raw = fields.Text(string="Raw Body")
    payload = fields.Json(string="Payload")
    event_type = fields.Char(string="Event Type", index=True)
    message_type = fields.Char(string="Message Type", default="inbound")
    idempotency_key = fields.Char(string="Idempotency Key", index=True)
    ordering_key = fields.Char(string="Ordering Key", index=True)
    signature_ok = fields.Boolean(string="Signature Verified", default=False)
    state = fields.Selection(
        [
            ("received", "Received"),
            ("queued", "Queued"),
            ("processing", "Processing"),
            ("done", "Done"),
            ("failed", "Failed (Retrying)"),
            ("dead", "Dead Letter (Exhausted)"),
            ("skipped", "Skipped (Duplicate)"),
        ],
        string="State",
        required=True,
        default="received",
        index=True,
    )
    priority = fields.Selection(
        related="endpoint_id.priority",
        string="Priority",
        store=True,
        index=True,
    )
    attempts = fields.Integer(string="Attempts", default=0)
    max_attempts = fields.Integer(string="Max Attempts", default=5)
    next_retry_at = fields.Datetime(string="Next Retry At", index=True)
    error_type = fields.Char(string="Error Type")
    error_details = fields.Text(string="Error Details")
    duration_ms = fields.Float(string="Duration (ms)")
    response_status = fields.Integer(string="Response Status")
    response_body = fields.Text(string="Response Body")

    _uniq_endpoint_idempotency = models.Constraint(
        "unique(endpoint_id, idempotency_key)",
        "Idempotency key must be unique per endpoint!",
    )

    @api.depends("uuid", "event_type", "endpoint_id.name", "state")
    def _compute_display_name(self):
        for rec in self:
            uuid_short = (rec.uuid or "")[:8]
            event = rec.event_type or (rec.endpoint_id.name if rec.endpoint_id else "Message")
            rec.display_name = f"[{uuid_short}] {event} ({rec.state})"

    def _is_blocked_by_ordering(self):
        """Returns True if an earlier message with the same ordering_key is still pending/processing."""
        self.ensure_one()
        if not self.ordering_key:
            return False
        earlier_count = self.search_count([
            ("endpoint_id", "=", self.endpoint_id.id),
            ("ordering_key", "=", self.ordering_key),
            ("id", "<", self.id),
            ("state", "in", ["queued", "processing", "failed"]),
        ])
        return earlier_count > 0

    def process_message(self):
        """Execute handler for this inbound message."""
        self.ensure_one()
        start_time = datetime.datetime.now()
        self.write({"state": "processing", "attempts": self.attempts + 1})

        try:
            with self.env.cr.savepoint():
                handler_type = self.endpoint_id.handler_type
                result = None

                if handler_type == "store_only":
                    result = {"status": "stored", "uuid": self.uuid}
                elif handler_type == "python":
                    code = self.endpoint_id.code or ""
                    eval_ctx = {
                        "payload": self.payload if self.payload is not None else {},
                        "headers": self.headers if self.headers is not None else {},
                        "message": self,
                        "endpoint": self.endpoint_id,
                        "env": self.env,
                        "record": False,
                        "records": False,
                        "datetime": datetime,
                        "dateutil": sys.modules.get("dateutil"),
                        "json": json,
                        "re": re,
                        "math": math,
                        "_import": _dynamic_import,
                        "_dynamic_import": _dynamic_import,
                        "callable": callable,
                        "RuntimeError": RuntimeError,
                        "ValueError": ValueError,
                        "TypeError": TypeError,
                        "ZeroDivisionError": ZeroDivisionError,
                        "AssertionError": AssertionError,
                        "log": lambda msg: _logger.info("[%s] %s", self.endpoint_id.name, msg),
                        "result": None,
                    }
                    _execute_safe_eval(code, eval_ctx, mode="exec")
                    result = eval_ctx.get("result")
                elif handler_type == "server_action":
                    action = self.endpoint_id.server_action_id
                    if action:
                        action_ctx = {
                            "active_model": self.endpoint_id.target_model_name or "connector.inbound.message",
                            "active_id": self.id,
                            "active_ids": [self.id],
                            "payload": self.payload or {},
                            "headers": self.headers or {},
                        }
                        result = action.with_context(**action_ctx).run()
                elif handler_type == "raw_model":
                    target_model = self.endpoint_id.target_model_name
                    if target_model and target_model in self.env:
                        raw_vals = {"x_payload": json.dumps(self.payload or {})}
                        if isinstance(self.payload, dict) and "id" in self.payload:
                            raw_vals["x_external_id"] = str(self.payload["id"])
                        created = self.env[target_model].sudo().create(raw_vals)  # sudo: dynamic creation of raw webhook payload record
                        result = {"id": created.id, "model": target_model}

            duration = (datetime.datetime.now() - start_time).total_seconds() * 1000.0
            resp_body = json.dumps(result) if result is not None else ""
            self.write({
                "state": "done",
                "duration_ms": duration,
                "response_status": 200,
                "response_body": resp_body,
                "error_type": False,
                "error_details": False,
            })
            return result

        except Exception as e:
            duration = (datetime.datetime.now() - start_time).total_seconds() * 1000.0
            err_type = type(e).__name__
            val_str = str(e)
            match = re.search(r"(\w+Error|\w+Exception)\(", val_str)
            if match:
                inner_name = match.group(1)
                if inner_name != err_type:
                    err_type = f"{err_type}: {inner_name}"
            err_details = traceback.format_exc()
            _logger.exception("Error processing message %s: %s", self.uuid, str(e))

            if self.attempts >= self.max_attempts:
                new_state = "dead"
                next_retry = False
            else:
                new_state = "failed"
                base_delay = 10
                delay = min(3600, base_delay * (2 ** self.attempts))
                jitter = random.uniform(0, delay * 0.5)
                next_retry = fields.Datetime.now() + datetime.timedelta(seconds=delay + jitter)

            self.write({
                "state": new_state,
                "duration_ms": duration,
                "error_type": err_type,
                "error_details": err_details,
                "next_retry_at": next_retry,
            })
            return None

    @api.model
    def _cron_process(self):
        """Claims and executes queued/failed messages in batch using SKIP LOCKED."""
        ICP = self.env["ir.config_parameter"].sudo()  # sudo: read system batch size parameter
        batch_size = int(ICP.get_param("dn_connector_base.default_batch_size", 100))
        now = fields.Datetime.now()

        query = SQL("""
            SELECT id FROM connector_inbound_message
            WHERE state IN ('queued', 'failed')
              AND (next_retry_at IS NULL OR next_retry_at <= %s)
            ORDER BY priority DESC, received_at ASC, id ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        """, now, batch_size)

        self.env.cr.execute(query)
        rows = self.env.cr.fetchall()
        if not rows:
            return

        message_ids = [row[0] for row in rows]
        messages = self.browse(message_ids)
        for message in messages:
            if message.ordering_key and message._is_blocked_by_ordering():
                continue
            message.process_message()

    @api.model
    def _cron_cleanup_retention(self):
        """Purges done and dead messages based on system retention days."""
        ICP = self.env["ir.config_parameter"].sudo()  # sudo: read retention parameters
        days_done = int(ICP.get_param("dn_connector_base.retention_days_done", 30))
        days_dead = int(ICP.get_param("dn_connector_base.retention_days_dead", 90))
        now = fields.Datetime.now()

        cutoff_done = now - datetime.timedelta(days=days_done)
        self.search([("state", "=", "done"), ("received_at", "<", cutoff_done)], limit=5000).unlink()

        cutoff_dead = now - datetime.timedelta(days=days_dead)
        self.search([("state", "=", "dead"), ("received_at", "<", cutoff_dead)], limit=5000).unlink()
