# -*- coding: utf-8 -*-
from psycopg2 import IntegrityError
from odoo.exceptions import ValidationError, AccessError
from odoo.tests import tagged, TransactionCase
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestInboundFramework(TransactionCase):
    """Unit tests for `connector.framework` model, presets, and auth schemes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Framework = cls.env["connector.framework"]
        cls.Endpoint = cls.env["connector.inbound.endpoint"]

    def test_01_framework_creation_and_defaults(self):
        """[AC-1] Test connector.framework creation and default field values."""
        framework = self.Framework.create({
            "name": "Custom Inbound System",
            "code": "custom_inbound",
        })
        self.assertTrue(framework.id)
        self.assertEqual(framework.name, "Custom Inbound System")
        self.assertEqual(framework.code, "custom_inbound")
        self.assertEqual(framework.auth_type, "none")
        self.assertEqual(framework.auth_header, "Authorization")
        self.assertEqual(framework.hmac_algo, "sha256")
        self.assertEqual(framework.hmac_encoding, "hex")
        self.assertEqual(framework.default_execution_mode, "deferred")
        self.assertTrue(framework.active)
        self.assertEqual(framework.endpoint_count, 0)

    def test_02_unique_code_constraint(self):
        """[AC-1] Test SQL constraint 'uniq_framework_code' prevents duplicate framework codes."""
        self.Framework.create({
            "name": "First Framework",
            "code": "unique_code_test",
        })
        with mute_logger("odoo.sql_db"), self.assertRaises((IntegrityError, ValidationError)):
            with self.env.cr.savepoint():
                self.Framework.create({
                    "name": "Second Framework Duplicate",
                    "code": "unique_code_test",
                })

    def test_03_builtin_presets_exist(self):
        """[AC-1] Test standard system framework presets exist with required configurations."""
        expected_presets = {
            "shopify": {
                "auth_type": "hmac",
                "hmac_algo": "sha256",
                "hmac_encoding": "base64",
                "auth_header": "X-Shopify-Hmac-Sha256",
                "event_type_header": "X-Shopify-Topic",
                "idempotency_header": "X-Shopify-Webhook-Id",
            },
            "github": {
                "auth_type": "hmac",
                "hmac_algo": "sha256",
                "hmac_encoding": "hex",
                "hmac_prefix": "sha256=",
                "auth_header": "X-Hub-Signature-256",
                "event_type_header": "X-GitHub-Event",
                "idempotency_header": "X-GitHub-Delivery",
            },
            "stripe": {
                "auth_type": "hmac",
                "hmac_algo": "sha256",
                "hmac_encoding": "hex",
                "signature_template": "t={timestamp},v1={signature}",
                "auth_header": "Stripe-Signature",
                "event_type_json_path": "type",
                "idempotency_json_path": "id",
            },
            "generic": {
                "auth_type": "none",
                "default_execution_mode": "deferred",
            },
        }

        for code, expected_vals in expected_presets.items():
            framework = self.Framework.search([("code", "=", code)], limit=1)
            self.assertTrue(framework, f"System preset '{code}' must exist in connector.framework")
            for field_name, expected_val in expected_vals.items():
                actual_val = getattr(framework, field_name)
                self.assertEqual(
                    actual_val,
                    expected_val,
                    f"Preset '{code}' field '{field_name}' expected {expected_val}, got {actual_val}",
                )

    def test_04_endpoint_count_compute(self):
        """[AC-1] Test endpoint_count computed field increments when child endpoints are created."""
        framework = self.Framework.create({
            "name": "Count Test Framework",
            "code": "count_test",
        })
        self.assertEqual(framework.endpoint_count, 0)

        self.Endpoint.create({
            "name": "Endpoint 1",
            "framework_id": framework.id,
        })
        self.Endpoint.create({
            "name": "Endpoint 2",
            "framework_id": framework.id,
        })
        framework.invalidate_recordset(["endpoint_count"])
        self.assertEqual(framework.endpoint_count, 2)

    def test_05_framework_auth_configurations(self):
        """[AC-5] Test configuring various auth schemes on framework (static_token, basic, hmac)."""
        static_fw = self.Framework.create({
            "name": "Static Token FW",
            "code": "static_fw",
            "auth_type": "static_token",
            "auth_header": "Authorization",
        })
        self.assertEqual(static_fw.auth_type, "static_token")

        basic_fw = self.Framework.create({
            "name": "Basic Auth FW",
            "code": "basic_fw",
            "auth_type": "basic",
            "auth_header": "Authorization",
        })
        self.assertEqual(basic_fw.auth_type, "basic")

        hmac_fw = self.Framework.create({
            "name": "HMAC SHA512 FW",
            "code": "hmac_sha512_fw",
            "auth_type": "hmac",
            "hmac_algo": "sha512",
            "hmac_encoding": "hex",
            "auth_header": "X-Custom-Sig",
        })
        self.assertEqual(hmac_fw.hmac_algo, "sha512")

    def test_06_framework_archiving(self):
        """[AC-1] Test framework archiving toggle."""
        framework = self.Framework.create({
            "name": "Archive Test",
            "code": "archive_test",
        })
        self.assertTrue(framework.active)
        framework.write({"active": False})
        self.assertFalse(framework.active)
        self.assertFalse(self.Framework.search([("code", "=", "archive_test")]))
        self.assertTrue(self.Framework.with_context(active_test=False).search([("code", "=", "archive_test")]))
