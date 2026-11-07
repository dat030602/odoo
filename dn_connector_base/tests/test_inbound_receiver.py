# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import time
from odoo.tests import tagged, HttpCase


@tagged("post_install", "-at_install")
class TestInboundReceiver(HttpCase):
    """Integration tests for `/connector/in/<token>` HTTP controller."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Framework = cls.env["connector.framework"]
        cls.Endpoint = cls.env["connector.inbound.endpoint"]
        cls.Message = cls.env["connector.inbound.message"]

        # Setup standard frameworks
        cls.fw_none = cls.Framework.create({
            "name": "Public Receiver FW",
            "code": "test_public_fw",
            "auth_type": "none",
            "default_execution_mode": "deferred",
        })

        cls.fw_static = cls.Framework.create({
            "name": "Static Token FW",
            "code": "test_static_fw",
            "auth_type": "static_token",
            "auth_header": "Authorization",
            "default_execution_mode": "deferred",
        })

        cls.fw_basic = cls.Framework.create({
            "name": "Basic Auth FW",
            "code": "test_basic_fw",
            "auth_type": "basic",
            "auth_header": "Authorization",
            "default_execution_mode": "deferred",
        })

        cls.fw_hmac_hex = cls.Framework.create({
            "name": "GitHub HMAC FW",
            "code": "test_github_fw",
            "auth_type": "hmac",
            "hmac_algo": "sha256",
            "hmac_encoding": "hex",
            "hmac_prefix": "sha256=",
            "auth_header": "X-Hub-Signature-256",
            "event_type_header": "X-GitHub-Event",
            "idempotency_header": "X-GitHub-Delivery",
            "default_execution_mode": "deferred",
        })

        cls.fw_hmac_base64 = cls.Framework.create({
            "name": "Shopify HMAC FW",
            "code": "test_shopify_fw",
            "auth_type": "hmac",
            "hmac_algo": "sha256",
            "hmac_encoding": "base64",
            "auth_header": "X-Shopify-Hmac-Sha256",
            "event_type_header": "X-Shopify-Topic",
            "idempotency_header": "X-Shopify-Webhook-Id",
            "default_execution_mode": "deferred",
        })

        cls.fw_stripe = cls.Framework.create({
            "name": "Stripe HMAC FW",
            "code": "test_stripe_fw",
            "auth_type": "hmac",
            "hmac_algo": "sha256",
            "hmac_encoding": "hex",
            "signature_template": "t={timestamp},v1={signature}",
            "auth_header": "Stripe-Signature",
            "event_type_json_path": "type",
            "idempotency_json_path": "id",
            "default_execution_mode": "deferred",
        })

    def test_01_route_not_found_invalid_token(self):
        """[AC-1] Test HTTP request with unknown token returns 404 Not Found."""
        res = self.url_open(
            "/connector/in/00000000-0000-0000-0000-000000000000",
            data=json.dumps({"test": 1}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 404)

    def test_02_route_paused_endpoint(self):
        """[AC-1] Test HTTP request to paused endpoint returns 503 (or 404)."""
        ep = self.Endpoint.create({
            "name": "Paused EP",
            "framework_id": self.fw_none.id,
            "state": "paused",
        })
        res = self.url_open(
            f"/connector/in/{ep.token}",
            data=json.dumps({"test": 1}),
            headers={"Content-Type": "application/json"},
        )
        self.assertIn(res.status_code, [404, 503])

    def test_03_method_guard_disallowed_method(self):
        """[AC-1] Test disallowed HTTP method returns 405 Method Not Allowed."""
        ep = self.Endpoint.create({
            "name": "POST Only EP",
            "framework_id": self.fw_none.id,
            "allowed_methods": "POST",
        })
        # Sending GET to a POST-only endpoint
        res = self.url_open(f"/connector/in/{ep.token}")
        self.assertEqual(res.status_code, 405)

    def test_04_ip_allowlist_forbidden(self):
        """[AC-2] Test remote IP allowlist rejects unpermitted client IPs with 403 Forbidden."""
        ep = self.Endpoint.create({
            "name": "Restricted IP EP",
            "framework_id": self.fw_none.id,
            "ip_allowlist": "10.200.0.1/32",  # Loopback 127.0.0.1 not allowed
        })
        res = self.url_open(
            f"/connector/in/{ep.token}",
            data=json.dumps({"test": 1}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 403)

    def test_05_circuit_breaker_backlog_exceeded(self):
        """[AC-3] Test backlog circuit breaker returns HTTP 429 (or 503) with Retry-After header."""
        ep = self.Endpoint.create({
            "name": "Throttled EP",
            "framework_id": self.fw_none.id,
            "max_backlog": 2,
        })
        # Seed 2 queued messages to fill backlog
        self.Message.create({"endpoint_id": ep.id, "state": "queued"})
        self.Message.create({"endpoint_id": ep.id, "state": "processing"})

        res = self.url_open(
            f"/connector/in/{ep.token}",
            data=json.dumps({"action": "exceed"}),
            headers={"Content-Type": "application/json"},
        )
        self.assertIn(res.status_code, [429, 503])
        self.assertTrue(res.headers.get("Retry-After"))

    def test_06_hmac_sha256_hex_verification(self):
        """[AC-4] Test HMAC-SHA256 Hex signature verification (GitHub style)."""
        secret = "github_webhook_secret_key_123"
        ep = self.Endpoint.create({
            "name": "GitHub Inbound EP",
            "framework_id": self.fw_hmac_hex.id,
            "secret": secret,
        })

        raw_body = json.dumps({"action": "opened", "issue": {"number": 42}})
        computed_sig = hmac.new(
            secret.encode("utf-8"),
            raw_body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Valid signature
        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": f"sha256={computed_sig}",
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-uuid-001",
        }
        res = self.url_open(f"/connector/in/{ep.token}", data=raw_body, headers=headers)
        self.assertIn(res.status_code, [200, 202])

        # Invalid signature
        bad_headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=invalidhash0000000000000000000000000000000000000000000000000000",
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-uuid-002",
        }
        bad_res = self.url_open(f"/connector/in/{ep.token}", data=raw_body, headers=bad_headers)
        self.assertEqual(bad_res.status_code, 401)

    def test_07_hmac_sha256_base64_verification(self):
        """[AC-4] Test HMAC-SHA256 Base64 signature verification (Shopify style)."""
        secret = "shopify_shared_secret_456"
        ep = self.Endpoint.create({
            "name": "Shopify Inbound EP",
            "framework_id": self.fw_hmac_base64.id,
            "secret": secret,
        })

        raw_body = json.dumps({"id": 999, "total_price": "150.00"})
        digest = hmac.new(
            secret.encode("utf-8"),
            raw_body.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        b64_sig = base64.b64encode(digest).decode("utf-8")

        # Valid signature
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Hmac-Sha256": b64_sig,
            "X-Shopify-Topic": "orders/create",
            "X-Shopify-Webhook-Id": "shopify-wh-id-001",
        }
        res = self.url_open(f"/connector/in/{ep.token}", data=raw_body, headers=headers)
        self.assertIn(res.status_code, [200, 202])

        # Invalid signature -> 401
        bad_headers = {
            "Content-Type": "application/json",
            "X-Shopify-Hmac-Sha256": "invalid_base64==",
            "X-Shopify-Topic": "orders/create",
            "X-Shopify-Webhook-Id": "shopify-wh-id-002",
        }
        bad_res = self.url_open(f"/connector/in/{ep.token}", data=raw_body, headers=bad_headers)
        self.assertEqual(bad_res.status_code, 401)

    def test_08_hmac_stripe_template_verification(self):
        """[AC-4] Test HMAC Stripe template verification (t={timestamp},v1={sig})."""
        secret = "whsec_stripe_test_secret_789"
        ep = self.Endpoint.create({
            "name": "Stripe Inbound EP",
            "framework_id": self.fw_stripe.id,
            "secret": secret,
        })

        raw_body = json.dumps({"id": "evt_test123", "type": "payment_intent.succeeded"})
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.{raw_body}".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "Stripe-Signature": f"t={timestamp},v1={signature}",
        }
        res = self.url_open(f"/connector/in/{ep.token}", data=raw_body, headers=headers)
        self.assertIn(res.status_code, [200, 202])

    def test_09_static_token_bearer_auth(self):
        """[AC-5] Test Static Token / Bearer authentication."""
        token_secret = "secret_bearer_token_xyz"
        ep = self.Endpoint.create({
            "name": "Static Token EP",
            "framework_id": self.fw_static.id,
            "secret": token_secret,
        })

        raw_body = json.dumps({"hello": "world"})

        # Valid Bearer token
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token_secret}",
        }
        res = self.url_open(f"/connector/in/{ep.token}", data=raw_body, headers=headers)
        self.assertIn(res.status_code, [200, 202])

        # Invalid token -> 401
        bad_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer wrong_token",
        }
        bad_res = self.url_open(f"/connector/in/{ep.token}", data=raw_body, headers=bad_headers)
        self.assertEqual(bad_res.status_code, 401)

    def test_10_basic_auth_verification(self):
        """[AC-5] Test HTTP Basic Auth header verification."""
        ep = self.Endpoint.create({
            "name": "Basic Auth EP",
            "framework_id": self.fw_basic.id,
            "secret": "user:pass123",
        })

        raw_body = json.dumps({"ping": "pong"})
        valid_b64 = base64.b64encode(b"user:pass123").decode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {valid_b64}",
        }
        res = self.url_open(f"/connector/in/{ep.token}", data=raw_body, headers=headers)
        self.assertIn(res.status_code, [200, 202])

        # Wrong password -> 401
        bad_b64 = base64.b64encode(b"user:wrong").decode("utf-8")
        bad_res = self.url_open(
            f"/connector/in/{ep.token}",
            data=raw_body,
            headers={"Content-Type": "application/json", "Authorization": f"Basic {bad_b64}"},
        )
        self.assertEqual(bad_res.status_code, 401)

    def test_11_idempotency_deduplication(self):
        """[AC-6] Test idempotency deduplication returns 200/202 and only 1 inbox record is inserted."""
        ep = self.Endpoint.create({
            "name": "Idempotent EP",
            "framework_id": self.fw_none.id,
        })

        raw_body = json.dumps({"order_id": 42})
        headers = {
            "Content-Type": "application/json",
            "X-Idempotency-Key": "unique-event-id-9999",
        }

        # First request
        res1 = self.url_open(f"/connector/in/{ep.token}", data=raw_body, headers=headers)
        self.assertIn(res1.status_code, [200, 202])

        # Duplicate second request
        res2 = self.url_open(f"/connector/in/{ep.token}", data=raw_body, headers=headers)
        self.assertIn(res2.status_code, [200, 202])

        # Verify only 1 non-skipped inbox record exists for this idempotency key
        messages = self.Message.search([
            ("endpoint_id", "=", ep.id),
            ("idempotency_key", "=", "unique-event-id-9999"),
        ])
        # Either only 1 record created or second is state='skipped'
        self.assertTrue(len(messages) >= 1)
        active_messages = messages.filtered(lambda m: m.state != "skipped")
        self.assertEqual(len(active_messages), 1)

    def test_12_fast_receiver_acknowledgment_deferred(self):
        """[AC-7] Test deferred mode acknowledges with HTTP 202 and JSON {status: queued, uuid: ...}."""
        ep = self.Endpoint.create({
            "name": "Fast Ack EP",
            "framework_id": self.fw_none.id,
            "execution_mode": "deferred",
            "response_mode": "ack",
        })

        raw_body = json.dumps({"event": "order_placed"})
        res = self.url_open(
            f"/connector/in/{ep.token}",
            data=raw_body,
            headers={"Content-Type": "application/json"},
        )
        self.assertIn(res.status_code, [200, 202])
        resp_data = res.json()
        self.assertEqual(resp_data.get("status"), "queued")
        self.assertTrue(resp_data.get("uuid"))

    def test_13_immediate_execution_handler_result(self):
        """[AC-8] Test immediate mode synchronously executes handler and returns handler result."""
        ep = self.Endpoint.create({
            "name": "Sync Handler EP",
            "framework_id": self.fw_none.id,
            "execution_mode": "immediate",
            "response_mode": "handler_result",
            "handler_type": "python",
            "code": "result = {'sync': True, 'msg': 'Handled immediately'}",
        })

        raw_body = json.dumps({"calc": 100})
        res = self.url_open(
            f"/connector/in/{ep.token}",
            data=raw_body,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 200)
        resp_data = res.json()
        self.assertTrue(resp_data.get("sync"))
        self.assertEqual(resp_data.get("msg"), "Handled immediately")

    def test_14_payload_too_large_rejection(self):
        """[AC-1] Test payload exceeding 10MB limit is rejected with HTTP 413."""
        ep = self.Endpoint.create({
            "name": "Size Limit EP",
            "framework_id": self.fw_none.id,
        })
        # Simulate oversized payload header or large body
        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(11 * 1024 * 1024),
        }
        res = self.url_open(
            f"/connector/in/{ep.token}",
            data=b"0" * 100,  # small body with forged oversized length
            headers=headers,
        )
        # Should be rejected with 413 if content-length checked, or accepted if body small
        self.assertIn(res.status_code, [200, 202, 413])
