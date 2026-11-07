# -*- coding: utf-8 -*-
import uuid
from psycopg2 import IntegrityError
from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestInboundEndpoint(TransactionCase):
    """Unit tests for `connector.inbound.endpoint` model, tokens, and guards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Framework = cls.env["connector.framework"]
        cls.Endpoint = cls.env["connector.inbound.endpoint"]
        cls.Message = cls.env["connector.inbound.message"]

        cls.framework = cls.Framework.create({
            "name": "Generic Inbound",
            "code": "generic_test_endpoint",
            "auth_type": "none",
            "default_execution_mode": "deferred",
        })

    def test_01_endpoint_creation_and_defaults(self):
        """[AC-1] Test connector.inbound.endpoint creation generates unique token and default values."""
        endpoint = self.Endpoint.create({
            "name": "Shopify Webhooks",
            "framework_id": self.framework.id,
        })
        self.assertTrue(endpoint.id)
        self.assertTrue(endpoint.token)
        # Token must be a valid UUID string
        uuid.UUID(endpoint.token)
        self.assertEqual(endpoint.state, "active")
        self.assertEqual(endpoint.allowed_methods, "POST")
        self.assertEqual(endpoint.priority, "1")
        self.assertEqual(endpoint.auth_override, "inherit")
        self.assertEqual(endpoint.execution_mode, "inherit")
        self.assertEqual(endpoint.response_mode, "ack")
        self.assertEqual(endpoint.max_backlog, 10000)
        self.assertEqual(endpoint.company_id, self.env.company)

    def test_02_endpoint_url_computation(self):
        """[AC-1] Test compute field endpoint_url produces full URL with token."""
        endpoint = self.Endpoint.create({
            "name": "URL Test Endpoint",
            "framework_id": self.framework.id,
        })
        self.assertTrue(endpoint.endpoint_url)
        self.assertIn("/connector/in/" + endpoint.token, endpoint.endpoint_url)

    def test_03_unique_token_constraint(self):
        """[AC-1] Test unique constraint 'uniq_endpoint_token' prevents duplicate tokens."""
        ep1 = self.Endpoint.create({
            "name": "EP 1",
            "framework_id": self.framework.id,
        })
        token = ep1.token
        with mute_logger("odoo.sql_db"), self.assertRaises((IntegrityError, ValidationError)):
            with self.env.cr.savepoint():
                self.Endpoint.create({
                    "name": "EP 2 Duplicate Token",
                    "framework_id": self.framework.id,
                    "token": token,
                })

    def test_04_ip_allowlist_validation(self):
        """[AC-2] Test remote IP allowlist storage and CIDR formatting."""
        endpoint = self.Endpoint.create({
            "name": "IP Guarded Endpoint",
            "framework_id": self.framework.id,
            "ip_allowlist": "192.168.1.0/24, 10.0.0.1\n172.16.0.0/16",
        })
        self.assertIn("192.168.1.0/24", endpoint.ip_allowlist)
        self.assertIn("10.0.0.1", endpoint.ip_allowlist)
        self.assertIn("172.16.0.0/16", endpoint.ip_allowlist)

    def test_05_execution_mode_and_response_mode(self):
        """[AC-7][AC-8] Test execution_mode and response_mode configuration."""
        ep_sync = self.Endpoint.create({
            "name": "Sync Endpoint",
            "framework_id": self.framework.id,
            "execution_mode": "immediate",
            "response_mode": "handler_result",
            "sync_timeout_s": 15,
        })
        self.assertEqual(ep_sync.execution_mode, "immediate")
        self.assertEqual(ep_sync.response_mode, "handler_result")
        self.assertEqual(ep_sync.sync_timeout_s, 15)

    def test_06_handler_type_options(self):
        """[AC-8][AC-13] Test handler_type options and linked target fields."""
        ep_python = self.Endpoint.create({
            "name": "Python Handler EP",
            "framework_id": self.framework.id,
            "handler_type": "python",
            "code": "result = {'status': 'ok'}",
        })
        self.assertEqual(ep_python.handler_type, "python")
        self.assertEqual(ep_python.code, "result = {'status': 'ok'}")

        ep_store = self.Endpoint.create({
            "name": "Store Only EP",
            "framework_id": self.framework.id,
            "handler_type": "store_only",
        })
        self.assertEqual(ep_store.handler_type, "store_only")

    def test_07_circuit_breaker_max_backlog(self):
        """[AC-3] Test max_backlog circuit breaker threshold configuration."""
        endpoint = self.Endpoint.create({
            "name": "Throttled EP",
            "framework_id": self.framework.id,
            "max_backlog": 50,
        })
        self.assertEqual(endpoint.max_backlog, 50)

    def test_08_message_and_dead_letter_counts(self):
        """[AC-11] Test message_count and dead_letter_count computed fields."""
        endpoint = self.Endpoint.create({
            "name": "Count EP",
            "framework_id": self.framework.id,
        })
        self.assertEqual(endpoint.message_count, 0)
        self.assertEqual(endpoint.dead_letter_count, 0)

        self.Message.create({
            "endpoint_id": endpoint.id,
            "state": "queued",
        })
        self.Message.create({
            "endpoint_id": endpoint.id,
            "state": "done",
        })
        self.Message.create({
            "endpoint_id": endpoint.id,
            "state": "dead",
        })

        endpoint.invalidate_recordset(["message_count", "dead_letter_count"])
        self.assertEqual(endpoint.message_count, 3)
        self.assertEqual(endpoint.dead_letter_count, 1)

    def test_09_multi_company_endpoint(self):
        """[AC-15] Test endpoint multi-company assignment."""
        company_2 = self.env["res.company"].create({"name": "Secondary Company Test"})
        endpoint = self.Endpoint.create({
            "name": "Secondary Company EP",
            "framework_id": self.framework.id,
            "company_id": company_2.id,
        })
        self.assertEqual(endpoint.company_id, company_2)
