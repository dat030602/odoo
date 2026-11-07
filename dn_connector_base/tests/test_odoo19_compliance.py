# -*- coding: utf-8 -*-
from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install")
class TestOdoo19Compliance(TransactionCase):
    """Unit tests for Odoo 19 compliance, ACLs, multi-company rules, and menus (AC-15, DEF-01 to DEF-08)."""

    def test_01_security_model_access_rules(self):
        """[AC-15] Test model access rules exist for all v2 models with correct prefix dn_connector_base (DEF-01)."""
        required_models = [
            "connector.framework",
            "connector.inbound.endpoint",
            "connector.inbound.message",
        ]
        IrModelAccess = self.env["ir.model.access"]
        for model_name in required_models:
            model = self.env["ir.model"].search([("model", "=", model_name)], limit=1)
            self.assertTrue(model, f"ir.model for {model_name} must exist")
            access = IrModelAccess.search([("model_id", "=", model.id)])
            self.assertTrue(access, f"ACL entries must exist for model {model_name}")

    def test_02_menu_hierarchy_registered(self):
        """[AC-15] Test root menu 'menu_connector_root' and inbound submenus are registered (DEF-07)."""
        Menu = self.env["ir.ui.menu"]
        root_menu = self.env.ref("dn_connector_base.menu_connector_root", raise_if_not_found=False)
        self.assertTrue(root_menu, "Root menu 'menu_connector_root' must be defined in views/menus.xml")

        inbound_menu = self.env.ref("dn_connector_base.menu_connector_inbound", raise_if_not_found=False)
        self.assertTrue(inbound_menu, "Inbound category menu 'menu_connector_inbound' must be defined")

        endpoint_menu = self.env.ref("dn_connector_base.menu_connector_inbound_endpoints", raise_if_not_found=False)
        self.assertTrue(endpoint_menu, "Menu 'menu_connector_inbound_endpoints' must be defined")

        inbox_menu = self.env.ref("dn_connector_base.menu_connector_inbound_messages", raise_if_not_found=False)
        self.assertTrue(inbox_menu, "Menu 'menu_connector_inbound_messages' must be defined")

        dlq_menu = self.env.ref("dn_connector_base.menu_connector_inbound_dead_letters", raise_if_not_found=False)
        self.assertTrue(dlq_menu, "Menu 'menu_connector_inbound_dead_letters' must be defined")

    def test_03_multi_company_record_rules(self):
        """[AC-15] Test multi-company ir.rule exists for connector.inbound.endpoint and connector.inbound.message."""
        IrRule = self.env["ir.rule"]
        models_to_check = ["connector.inbound.endpoint", "connector.inbound.message"]
        for model_name in models_to_check:
            rules = IrRule.search([("model_id.model", "=", model_name)])
            company_rules = rules.filtered(lambda r: "company_id" in (r.domain_force or ""))
            self.assertTrue(company_rules, f"Multi-company ir.rule must exist for {model_name}")

    def test_04_system_retention_settings_fields(self):
        """[AC-15] Test res.config.settings has connector retention fields."""
        ConfigSettings = self.env["res.config.settings"]
        self.assertTrue(
            hasattr(ConfigSettings, "connector_retention_days_done"),
            "res.config.settings must define connector_retention_days_done",
        )
        self.assertTrue(
            hasattr(ConfigSettings, "connector_retention_days_dead"),
            "res.config.settings must define connector_retention_days_dead",
        )
        self.assertTrue(
            hasattr(ConfigSettings, "connector_default_batch_size"),
            "res.config.settings must define connector_default_batch_size",
        )
        self.assertTrue(
            hasattr(ConfigSettings, "connector_lock_timeout"),
            "res.config.settings must define connector_lock_timeout",
        )
