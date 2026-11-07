# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import ipaddress
import json
import logging
from psycopg2 import IntegrityError
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ConnectorInboundController(http.Controller):

    @http.route(
        "/connector/in/<string:token>",
        type="http",
        auth="public",
        methods=["GET", "POST", "PUT", "PATCH"],
        csrf=False,
        save_session=False,
    )
    def inbound_receiver(self, token, **kwargs):
        # 1. Resolve endpoint
        endpoint = request.env["connector.inbound.endpoint"].sudo().search(  # sudo: public webhook endpoint lookup by token
            [("token", "=", token)], limit=1
        )
        if not endpoint or endpoint.state == "draft":
            return request.make_response(
                json.dumps({"error": "Endpoint not found"}),
                headers=[("Content-Type", "application/json")],
                status=404,
            )
        if endpoint.state == "paused":
            return request.make_response(
                json.dumps({"error": "Endpoint paused"}),
                headers=[("Content-Type", "application/json")],
                status=503,
            )
        if endpoint.state != "active":
            return request.make_response(
                json.dumps({"error": "Endpoint not active"}),
                headers=[("Content-Type", "application/json")],
                status=404,
            )

        # 2. Method guard
        method = request.httprequest.method
        allowed = endpoint.allowed_methods
        if allowed == "POST" and method != "POST":
            return request.make_response(
                json.dumps({"error": "Method Not Allowed"}),
                headers=[("Content-Type", "application/json")],
                status=405,
            )
        elif allowed == "POST_PUT" and method not in ("POST", "PUT"):
            return request.make_response(
                json.dumps({"error": "Method Not Allowed"}),
                headers=[("Content-Type", "application/json")],
                status=405,
            )

        # 3. IP Allowlist
        if endpoint.ip_allowlist:
            client_ip_str = request.httprequest.headers.get("X-Forwarded-For")
            if client_ip_str:
                client_ip_str = client_ip_str.split(",")[0].strip()
            else:
                client_ip_str = request.httprequest.remote_addr
            try:
                client_ip = ipaddress.ip_address(client_ip_str)
                allowed_entries = [
                    entry.strip()
                    for entry in endpoint.ip_allowlist.replace("\n", ",").split(",")
                    if entry.strip()
                ]
                matched = False
                for allowed_net in allowed_entries:
                    try:
                        net = (
                            ipaddress.ip_network(allowed_net, strict=False)
                            if "/" in allowed_net
                            else ipaddress.ip_network(f"{allowed_net}/32", strict=False)
                        )
                        if client_ip in net:
                            matched = True
                            break
                    except ValueError:
                        continue
                if not matched:
                    return request.make_response(
                        json.dumps({"error": "Forbidden"}),
                        headers=[("Content-Type", "application/json")],
                        status=403,
                    )
            except ValueError:
                return request.make_response(
                    json.dumps({"error": "Forbidden"}),
                    headers=[("Content-Type", "application/json")],
                    status=403,
                )

        # 4. Payload size & Backlog circuit breaker
        raw_body_bytes = request.httprequest.get_data()
        content_length = request.httprequest.content_length
        if (content_length and content_length > 10 * 1024 * 1024) or (
            raw_body_bytes and len(raw_body_bytes) > 10 * 1024 * 1024
        ):
            return request.make_response(
                json.dumps({"error": "Payload Too Large"}),
                headers=[("Content-Type", "application/json")],
                status=413,
            )

        backlog = request.env["connector.inbound.message"].sudo().search_count([  # sudo: read endpoint message backlog count
            ("endpoint_id", "=", endpoint.id),
            ("state", "in", ["queued", "processing"]),
        ])
        if backlog >= endpoint.max_backlog:
            return request.make_response(
                json.dumps({"error": "Backlog exceeded, throttling"}),
                headers=[
                    ("Content-Type", "application/json"),
                    ("Retry-After", "30"),
                ],
                status=429,
            )

        # 5. Authentication & HMAC Verification
        fw = endpoint.framework_id
        auth_type = (
            endpoint.auth_override
            if endpoint.auth_override != "inherit"
            else (fw.auth_type or "none")
        )
        auth_header_name = fw.auth_header or "Authorization"
        secret = endpoint.secret or ""
        signature_ok = False

        if auth_type == "none":
            signature_ok = True
        elif auth_type == "static_token":
            auth_header = request.httprequest.headers.get(auth_header_name, "")
            provided_token = auth_header
            if provided_token.startswith("Bearer "):
                provided_token = provided_token[7:].strip()
            if not secret or not hmac.compare_digest(provided_token, secret):
                return request.make_response(
                    json.dumps({"error": "Unauthorized"}),
                    headers=[("Content-Type", "application/json")],
                    status=401,
                )
            signature_ok = True
        elif auth_type == "basic":
            auth_header = request.httprequest.headers.get(auth_header_name, "")
            if not auth_header.startswith("Basic "):
                return request.make_response(
                    json.dumps({"error": "Unauthorized"}),
                    headers=[("Content-Type", "application/json")],
                    status=401,
                )
            try:
                decoded = base64.b64decode(auth_header[6:].strip()).decode("utf-8")
            except Exception:
                return request.make_response(
                    json.dumps({"error": "Unauthorized"}),
                    headers=[("Content-Type", "application/json")],
                    status=401,
                )
            if not secret or not hmac.compare_digest(decoded, secret):
                return request.make_response(
                    json.dumps({"error": "Unauthorized"}),
                    headers=[("Content-Type", "application/json")],
                    status=401,
                )
            signature_ok = True
        elif auth_type == "hmac":
            sig_header = request.httprequest.headers.get(auth_header_name, "")
            if not sig_header or not secret:
                return request.make_response(
                    json.dumps({"error": "Unauthorized"}),
                    headers=[("Content-Type", "application/json")],
                    status=401,
                )

            raw_body_str = raw_body_bytes.decode("utf-8", errors="replace")

            if fw.signature_template and "t=" in fw.signature_template:
                parts = dict(
                    part.split("=", 1)
                    for part in sig_header.split(",")
                    if "=" in part
                )
                ts = parts.get("t", "")
                sig = parts.get("v1", "")
                if not ts or not sig:
                    return request.make_response(
                        json.dumps({"error": "Unauthorized"}),
                        headers=[("Content-Type", "application/json")],
                        status=401,
                        )
                signed_payload = f"{ts}.{raw_body_str}".encode("utf-8")
                computed = hmac.new(
                    secret.encode("utf-8"), signed_payload, hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(computed, sig):
                    return request.make_response(
                        json.dumps({"error": "Unauthorized"}),
                        headers=[("Content-Type", "application/json")],
                        status=401,
                    )
                signature_ok = True
            else:
                if fw.hmac_prefix and sig_header.startswith(fw.hmac_prefix):
                    sig_header = sig_header[len(fw.hmac_prefix):]

                algo_map = {
                    "sha256": hashlib.sha256,
                    "sha1": hashlib.sha1,
                    "sha512": hashlib.sha512,
                }
                hasher = algo_map.get(fw.hmac_algo or "sha256", hashlib.sha256)
                mac = hmac.new(secret.encode("utf-8"), raw_body_bytes, hasher)
                if fw.hmac_encoding == "base64":
                    computed = base64.b64encode(mac.digest()).decode("utf-8")
                else:
                    computed = mac.hexdigest()

                if not hmac.compare_digest(computed, sig_header):
                    return request.make_response(
                        json.dumps({"error": "Unauthorized"}),
                        headers=[("Content-Type", "application/json")],
                        status=401,
                    )
                signature_ok = True

        # 6. Extract Keys & Deduplication
        raw_text = raw_body_bytes.decode("utf-8", errors="replace")
        payload_json = None
        if raw_text:
            try:
                payload_json = json.loads(raw_text)
            except Exception:
                payload_json = None

        def _extract_json_path(data, path):
            if not path or not isinstance(data, dict):
                return None
            node = data
            for k in path.split("."):
                if isinstance(node, dict):
                    node = node.get(k)
                else:
                    return None
            return node

        event_type = None
        if fw.event_type_header:
            event_type = request.httprequest.headers.get(fw.event_type_header)
        if not event_type and fw.event_type_json_path and payload_json:
            event_type = _extract_json_path(payload_json, fw.event_type_json_path)

        idempotency_key = None
        if fw.idempotency_header:
            idempotency_key = request.httprequest.headers.get(fw.idempotency_header)
        if not idempotency_key:
            idempotency_key = request.httprequest.headers.get("X-Idempotency-Key")
        if not idempotency_key and fw.idempotency_json_path and payload_json:
            val = _extract_json_path(payload_json, fw.idempotency_json_path)
            if val is not None:
                idempotency_key = str(val)

        ordering_key = None
        if endpoint.ordering_key == "entity_id":
            val = _extract_json_path(payload_json, endpoint.ordering_json_path or "id")
            if val is not None:
                ordering_key = str(val)
        elif endpoint.ordering_key == "event_type":
            ordering_key = event_type

        # Deduplication check
        if idempotency_key:
            existing = request.env["connector.inbound.message"].sudo().search([  # sudo: check existing duplicate message
                ("endpoint_id", "=", endpoint.id),
                ("idempotency_key", "=", idempotency_key),
            ], limit=1)
            if existing:
                return request.make_response(
                    json.dumps({
                        "status": "duplicate",
                        "uuid": existing.uuid,
                        "state": existing.state,
                        "message": "Message already accepted and processed.",
                    }),
                    headers=[("Content-Type", "application/json")],
                    status=200,
                )

        # 7. Create Inbox Record
        client_ip_str = request.httprequest.headers.get("X-Forwarded-For")
        if client_ip_str:
            client_ip_str = client_ip_str.split(",")[0].strip()
        else:
            client_ip_str = request.httprequest.remote_addr

        exec_mode = (
            endpoint.execution_mode
            if endpoint.execution_mode != "inherit"
            else (fw.default_execution_mode or "deferred")
        )
        initial_state = (
            "processing"
            if exec_mode == "immediate" or endpoint.response_mode == "handler_result"
            else "queued"
        )

        msg_vals = {
            "endpoint_id": endpoint.id,
            "remote_ip": client_ip_str,
            "method": method,
            "headers": dict(request.httprequest.headers),
            "body_raw": raw_text,
            "payload": payload_json,
            "event_type": event_type,
            "idempotency_key": idempotency_key,
            "ordering_key": ordering_key,
            "signature_ok": signature_ok,
            "state": initial_state,
        }

        try:
            with request.env.cr.savepoint():
                message = request.env["connector.inbound.message"].sudo().create(msg_vals)  # sudo: persist inbound webhook message
            request.env.cr.commit()
        except IntegrityError:
            # Concurrency race condition on _uniq_endpoint_idempotency:
            # another request with the same idempotency_key committed right before our create().
            # Catch UniqueViolation, rollback savepoint, fetch existing record, and return duplicate acknowledgment.
            if idempotency_key:
                existing = request.env["connector.inbound.message"].sudo().search([  # sudo: fetch concurrent duplicate message
                    ("endpoint_id", "=", endpoint.id),
                    ("idempotency_key", "=", idempotency_key),
                ], limit=1)
                if existing:
                    return request.make_response(
                        json.dumps({
                            "status": "duplicate",
                            "uuid": existing.uuid,
                            "state": existing.state,
                            "message": "Message already accepted and processed.",
                        }),
                        headers=[("Content-Type", "application/json")],
                        status=200,
                    )
            raise

        # 8. Dispatch or Acknowledge
        if exec_mode == "immediate" or endpoint.response_mode == "handler_result":
            result = message.process_message()
            request.env.cr.commit()
            resp_body = json.dumps(result) if result is not None else "{}"
            return request.make_response(
                resp_body,
                headers=[("Content-Type", "application/json")],
                status=200,
            )
        else:
            ack_status = endpoint.fallback_status or 202
            return request.make_response(
                json.dumps({"status": "queued", "uuid": message.uuid}),
                headers=[("Content-Type", "application/json")],
                status=ack_status,
            )
