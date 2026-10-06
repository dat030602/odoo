# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch
from odoo.addons.ai.utils.llm_api_service import LLMApiService
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged("post_install", "-at_install", "dn_ai_document_import")
class TestDnAiDocumentImport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_order_model = cls.env["ir.model"].search([("model", "=", "sale.order")], limit=1)
        cls.partner = cls.env["res.partner"].create({
            "name": "Azure Interior",
            "email": "azure@example.com",
            "vat": "US123456789",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Custom Acoustic Desk",
            "default_code": "DESK001",
            "list_price": 250.0,
        })
        cls.template = cls.env.ref("dn_ai_document_import.dn_ai_import_template_sale_order")

    def test_01_schema_generation(self):
        """Test JSON Schema generated follows OpenAI strict requirements."""
        schema = self.template._build_json_schema()
        self.assertEqual(schema["type"], "object")
        self.assertIn("partner", schema["properties"])
        self.assertIn("lines", schema["properties"])
        self.assertIn("lines", schema["required"])
        self.assertFalse(schema["additionalProperties"])
        # Check line item schema
        line_schema = schema["properties"]["lines"]["items"]
        self.assertEqual(line_schema["type"], "object")
        self.assertIn("product", line_schema["properties"])
        self.assertFalse(line_schema["additionalProperties"])

    def test_02_server_action_synchronization(self):
        """Test that server action is automatically generated and linked."""
        action = self.template.action_id
        self.assertTrue(action)
        self.assertEqual(action.binding_model_id.model, "sale.order")
        self.assertEqual(action.state, "code")
        self.assertIn("action_open_wizard", action.code)

    def test_03_fuzzy_matching(self):
        """Test fuzzy matching logic using difflib."""
        mapping_partner = self.template.mapping_ids.filtered(lambda m: m.key == "partner")
        # 'Asure Interior' should match 'Azure Interior' with threshold 80
        matched = mapping_partner.match_record("Asure Interior")
        self.assertEqual(matched.id, self.partner.id)

        # High threshold should fail
        mapping_partner.fuzzy_threshold = 98
        matched_fail = mapping_partner.match_record("Asure Interior")
        self.assertFalse(matched_fail)

    def test_04_create_if_missing(self):
        """Test creating related records on the fly when missing."""
        mapping_partner = self.template.mapping_ids.filtered(lambda m: m.key == "partner")
        mapping_partner.create_if_missing = True
        new_partner = mapping_partner.match_record("Completely Unknown Client Inc")
        self.assertTrue(new_partner)
        self.assertEqual(new_partner.name, "Completely Unknown Client Inc")

    def test_05_wizard_full_flow(self):
        """Test complete import process from PDF attachment to Sale Order."""
        attachment = self.env["ir.attachment"].create({
            "name": "sample_order.pdf",
            "datas": "JVBERi0xLjQKJcTl8uXrCg==", # dummy PDF header
            "mimetype": "application/pdf",
        })

        mock_ai_output = [
            json.dumps({
                "partner": "Azure Interior",
                "client_order_ref": "PO-2026-999",
                "date_order": "2026-10-06",
                "validity_date": "2026-11-06",
                "lines": [
                    {
                        "product": "Custom Acoustic Desk",
                        "description": "Desk order line item",
                        "quantity": 3.0,
                        "price_unit": 220.0,
                        "discount": 5.0,
                    }
                ]
            })
        ]

        with patch.object(LLMApiService, "request_llm", return_value=mock_ai_output):
            wizard = self.env["dn.ai.import.wizard"].create({
                "template_id": self.template.id,
                "attachment_ids": [(6, 0, [attachment.id])],
            })
            # 1. Digitize & Preview
            res = wizard.action_extract()
            self.assertEqual(wizard.state, "preview")
            self.assertTrue(wizard.value_ids)

            # Check matching
            partner_val = wizard.value_ids.filtered(lambda v: v.key == "partner")
            self.assertEqual(partner_val.matched_res_id, self.partner.id)
            self.assertEqual(partner_val.status, "matched")

            # 2. Confirm & Create Order
            confirm_res = wizard.action_confirm()
            order = self.env["sale.order"].browse(confirm_res["res_id"])
            self.assertTrue(order)
            self.assertEqual(order.partner_id.id, self.partner.id)
            self.assertEqual(order.client_order_ref, "PO-2026-999")
            self.assertEqual(len(order.order_line), 1)
            self.assertEqual(order.order_line.product_id.id, self.product.id)
            self.assertEqual(order.order_line.product_uom_qty, 3.0)
            self.assertEqual(order.order_line.price_unit, 220.0)
            self.assertEqual(order.order_line.discount, 5.0)

    def test_06_invalid_json_handling(self):
        """Test error handling when AI response is not valid JSON."""
        attachment = self.env["ir.attachment"].create({
            "name": "bad.pdf",
            "datas": "JVBERi0xLjQKJcTl8uXrCg==",
            "mimetype": "application/pdf",
        })
        with patch.object(LLMApiService, "request_llm", return_value=["This is plain text, not JSON"]):
            with self.assertRaises(UserError):
                self.template.extract_document(attachment)
