# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    connector_retention_days_done = fields.Integer(
        string="Retention Days (Done Messages)",
        config_parameter="dn_connector_base.retention_days_done",
        default=30,
    )
    connector_retention_days_dead = fields.Integer(
        string="Retention Days (Dead Letters)",
        config_parameter="dn_connector_base.retention_days_dead",
        default=90,
    )
    connector_default_batch_size = fields.Integer(
        string="Inbound Processor Batch Size",
        config_parameter="dn_connector_base.default_batch_size",
        default=100,
    )
    connector_lock_timeout = fields.Integer(
        string="Message Lock Timeout (Seconds)",
        config_parameter="dn_connector_base.lock_timeout",
        default=60,
    )
    setup_guide_url = fields.Char(
        string="Setup Guide URL",
        compute="_compute_setup_guide_url",
    )

    def _compute_setup_guide_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")  # sudo: read base url for setup guide link
        base_url = base_url.rstrip("/") if base_url else ""
        for record in self:
            record.setup_guide_url = f"{base_url}/connector/docs/setup"

    def action_open_setup_guide(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/connector/docs/setup",
            "target": "new",
        }

    def action_open_connector_setup_guide(self):
        """Compatibility alias for action_open_setup_guide."""
        return self.action_open_setup_guide()
