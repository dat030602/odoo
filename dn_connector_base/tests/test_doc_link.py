# -*- coding: utf-8 -*-
from odoo.tests import tagged, HttpCase, TransactionCase


@tagged("post_install", "-at_install")
class TestDocLinkSettings(TransactionCase):
    """Unit tests for res.config.settings documentation link and action."""

    def test_01_action_open_setup_guide_action(self):
        """Verify action_open_setup_guide returns an act_url action opening /connector/docs/setup."""
        settings = self.env["res.config.settings"].create({})
        action = settings.action_open_setup_guide()

        self.assertIsInstance(action, dict, "Action must be a dictionary")
        self.assertEqual(action.get("type"), "ir.actions.act_url", "Action type must be ir.actions.act_url")
        self.assertEqual(action.get("url"), "/connector/docs/setup", "URL must point to /connector/docs/setup")
        self.assertEqual(action.get("target"), "new", "Target must be 'new' to open in a new tab")

    def test_02_action_open_connector_setup_guide_alias(self):
        """Verify compatibility alias action_open_connector_setup_guide returns identical act_url."""
        settings = self.env["res.config.settings"].create({})
        action = settings.action_open_connector_setup_guide()

        self.assertIsInstance(action, dict)
        self.assertEqual(action.get("type"), "ir.actions.act_url")
        self.assertEqual(action.get("url"), "/connector/docs/setup")
        self.assertEqual(action.get("target"), "new")

    def test_03_setup_guide_url_computation(self):
        """Verify setup_guide_url computed field formats the full URL with web.base.url."""
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
        # sudo: read base url for test assertion
        settings = self.env["res.config.settings"].create({})
        expected_url = f"{base_url}/connector/docs/setup"
        self.assertEqual(
            settings.setup_guide_url,
            expected_url,
            "setup_guide_url must concatenate base URL and /connector/docs/setup",
        )

    def test_04_markdown_visual_components_rendering(self):
        """Verify markdown images and raw HTML cards pass-through render cleanly."""
        from odoo.addons.dn_connector_base.controllers.docs import ConnectorDocsController
        controller = ConnectorDocsController()

        test_md = """
# Test Document

![Endpoints Screenshot](/dn_connector_base/static/description/screenshot_endpoints.png)

![Relative Image](static/description/screenshot_settings.png)

<div class="system-param-card">
    <div class="param-header">
        <span>Parameters</span>
    </div>
    <div class="param-row">
        <span class="param-label">Base URL</span>
        <span class="param-key">web.base.url</span>
        <span class="param-value">https://odoo.test</span>
    </div>
</div>

<svg width="200" height="100" viewBox="0 0 200 100">
    <rect width="200" height="100" fill="#0284c7"/>
</svg>
"""
        content_html, _ = controller._convert_markdown_to_html(test_md, "https://odoo.test")

        self.assertIn('<div class="doc-image-box">', content_html)
        self.assertIn('<img src="/dn_connector_base/static/description/screenshot_endpoints.png"', content_html)
        self.assertIn('<img src="/dn_connector_base/static/description/screenshot_settings.png"', content_html)
        self.assertIn('<div class="doc-image-caption"><i class="fa fa-info-circle"></i> Endpoints Screenshot</div>', content_html)
        self.assertIn('<div class="system-param-card">', content_html)
        self.assertIn('<span class="param-key">web.base.url</span>', content_html)
        self.assertIn('<svg width="200" height="100"', content_html)


@tagged("post_install", "-at_install")
class TestDocLinkHttp(HttpCase):
    """HTTP integration tests for the /connector/docs/setup controller route."""

    def test_01_setup_guide_route_authenticated(self):
        """Verify authenticated user can access /connector/docs/setup and receives 200 HTML with styles."""
        self.authenticate("admin", "admin")
        response = self.url_open("/connector/docs/setup")

        self.assertEqual(response.status_code, 200, "Route must return HTTP 200 for authenticated users")
        content_type = response.headers.get("Content-Type", "")
        self.assertIn("text/html", content_type, "Response Content-Type must be text/html")

        # Verify key setup guide sections and visual CSS classes are present in HTML
        body = response.text
        self.assertIn("Setup Guide", body)
        self.assertIn("Shopify", body)
        self.assertIn("GitHub", body)
        self.assertIn("Stripe", body)
        self.assertIn("Dead Letter Queue", body)
        self.assertIn("Retention", body)
        self.assertIn("FOR UPDATE SKIP LOCKED", body)
        self.assertIn(".doc-image-box", body)
        self.assertIn(".system-param-card", body)
        self.assertIn(".param-row", body)

    def test_02_setup_guide_route_unauthenticated(self):
        """Verify unauthenticated user cannot access /connector/docs/setup and is redirected to login."""
        response = self.url_open("/connector/docs/setup")
        # In Odoo, auth='user' redirects unauthenticated requests to /web/login
        self.assertTrue(
            "/web/login" in response.url or response.status_code in (302, 303),
            "Unauthenticated request must redirect to /web/login",
        )
