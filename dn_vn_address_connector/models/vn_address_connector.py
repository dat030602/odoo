# -*- coding: utf-8 -*-
import json
import logging
import urllib.request
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class VnAddressConnectorSync(models.Model):
    _name = "vn.address.connector.sync"
    _description = "Vietnam Address Connector Sync Service (v1)"

    name = fields.Char(string="Name", default="Address Sync v1")

    @api.model
    def enqueue_payload_v1(self, payload, process_now=True):
        """Enqueue payload into connector inbox and optionally process immediately."""
        endpoint = self.env.ref("dn_vn_address_connector.endpoint_vn_address_v1", raise_if_not_found=False)
        if not endpoint:
            endpoint = self.env["connector.inbound.endpoint"].search([
                ("name", "ilike", "Open API v1 Address Ingestion"),
            ], limit=1)
        if not endpoint:
            raise UserError(_("Inbound endpoint for Open API v1 not found."))

        # sudo: create inbound connector message bypassing user ACL restrictions
        message = self.env["connector.inbound.message"].sudo().create({
            "endpoint_id": endpoint.id,
            "company_id": endpoint.company_id.id,
            "event_type": "address_sync_v1",
            "payload": payload,
            "body_raw": json.dumps(payload),
            "state": "ready" if not process_now else "received",
        })

        if process_now:
            message.process_message()

        return message

    def action_pull_and_enqueue_v1(self):
        """Pull data from Open API v1 and enqueue into connector framework."""
        # sudo: read global system parameter for api endpoint url
        base_url = self.env["ir.config_parameter"].sudo().get_param(
            "dn_vn_address.api_url", "https://provinces.open-api.vn/api/v1"
        ).rstrip("/")

        req_p = urllib.request.Request(f"{base_url}/p/", headers={"User-Agent": "Odoo-Connector-VN/19.0"})
        req_d = urllib.request.Request(f"{base_url}/d/", headers={"User-Agent": "Odoo-Connector-VN/19.0"})
        req_w = urllib.request.Request(f"{base_url}/w/", headers={"User-Agent": "Odoo-Connector-VN/19.0"})

        try:
            with urllib.request.urlopen(req_p, timeout=30) as resp:
                provinces = json.loads(resp.read().decode("utf-8"))
            with urllib.request.urlopen(req_d, timeout=30) as resp:
                districts = json.loads(resp.read().decode("utf-8"))
            with urllib.request.urlopen(req_w, timeout=30) as resp:
                wards = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            _logger.error("Failed to pull from Open API v1: %s", str(e))
            raise UserError(_("Failed to pull data from Open API v1: %s") % str(e))

        payload = {
            "provinces": provinces,
            "districts": districts,
            "wards": wards,
        }
        msg = self.enqueue_payload_v1(payload, process_now=True)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connector Ingestion Complete"),
                "message": _("Address v1 data queued and processed via message %s") % msg.id,
                "type": "success",
                "sticky": False,
            },
        }
