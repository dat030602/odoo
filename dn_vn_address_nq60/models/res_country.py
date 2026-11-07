# -*- coding: utf-8 -*-
import json
import logging
import urllib.request
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    map_with_state_ids = fields.Many2many(
        "res.country.state",
        "res_country_state_map_rel",
        "res_country_state_id",
        "map_with_state_id",
        string="Map With States (Merged)",
        copy=False,
    )

    def action_merge_state_nq60(self):
        """Merge absorbed legacy provinces into this anchor province."""
        self.ensure_one()
        if not self.map_with_state_ids:
            return False
        absorbed = self.map_with_state_ids
        partners = self.env["res.partner"].with_context(active_test=False).search([("state_id", "in", absorbed.ids)])
        if partners:
            partners.write({"state_id": self.id})
        absorbed.write({"active": False})
        return True

    @api.model
    def do_merge_state_nq60(self):
        """Execute merger for all anchor provinces with map_with_state_ids."""
        records = self.search([("map_with_state_ids", "!=", False)])
        for state in records:
            state.action_merge_state_nq60()
        return True

    def action_sync_nq60_v2(self):
        """Fetch and sync consolidated provinces and wards from Open API v2."""
        self._sync_nq60_v2()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("NQ60 Sync Completed"),
                "message": _("Vietnam administrative units (NQ60 v2) have been synchronized successfully."),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def _cron_sync_nq60_v2(self):
        """Cron entry point for syncing NQ60 v2 administrative units."""
        return self._sync_nq60_v2()

    @api.model
    def _fetch_api_json_v2(self, url, timeout=30):
        """Fetch JSON data from API v2 endpoint."""
        req = urllib.request.Request(url, headers={"User-Agent": "Odoo-DN-VN-Address-NQ60/19.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            _logger.error("Failed to fetch NQ60 data from %s: %s", url, str(e))
            raise UserError(_("Failed to fetch data from %s: %s") % (url, str(e)))

    @api.model
    def _sync_nq60_v2(self):
        """Fetch 34 provinces and 3,321 wards from Open API v2 with legacy mapping."""
        base_url = self.env["ir.config_parameter"].sudo().get_param(
            "dn_vn_address_nq60.api_url", "https://provinces.open-api.vn/api/v2"
        ).rstrip("/")

        vn = self.env.ref("base.vn", raise_if_not_found=False)
        if not vn:
            vn = self.env["res.country"].search([("code", "=", "VN")], limit=1)
        if not vn:
            raise UserError(_("Country Vietnam (code VN) not found."))

        # 1. Sync 34 Provinces (/p/)
        provinces_url = f"{base_url}/p/"
        provinces = self._fetch_api_json_v2(provinces_url)
        if not isinstance(provinces, list):
            _logger.warning("Expected list from %s, got %s", provinces_url, type(provinces))
            return False

        existing_states_by_vn_code = {
            s.vn_code: s for s in self.search([("country_id", "=", vn.id), ("vn_code", "!=", False)])
        }
        existing_states_by_code = {
            s.code: s for s in self.search([("country_id", "=", vn.id)])
        }

        states_to_create = []
        for p in provinces:
            p_code = p.get("code")
            p_name = p.get("name")
            p_codename = p.get("codename") or ""
            if not p_code:
                continue

            state = existing_states_by_vn_code.get(p_code) or existing_states_by_code.get(str(p_code))
            if state:
                state.write({
                    "name": p_name,
                    "vn_code": p_code,
                    "name_extension": p_codename,
                })
                existing_states_by_vn_code[p_code] = state
            else:
                states_to_create.append({
                    "name": p_name,
                    "code": str(p_code),
                    "vn_code": p_code,
                    "name_extension": p_codename,
                    "country_id": vn.id,
                })

        if states_to_create:
            new_states = self.create(states_to_create)
            for s in new_states:
                if s.vn_code:
                    existing_states_by_vn_code[s.vn_code] = s

        # State lookup
        state_map = {
            s.vn_code: s.id for s in self.search([("country_id", "=", vn.id), ("vn_code", "!=", False)])
        }

        # 2. Sync 3,321 Wards (/w/)
        wards_url = f"{base_url}/w/"
        try:
            wards = self._fetch_api_json_v2(wards_url)
        except Exception as e:
            _logger.warning("Could not sync wards v2: %s", str(e))
            wards = []

        Ward = self.env["res.country.ward"]
        existing_wards_by_code = {
            str(w.code): w for w in Ward.search([])
        }

        wards_to_create = []
        for w in wards:
            w_code = str(w.get("code"))
            w_name = w.get("name")
            p_code = w.get("province_code")
            w_codename = w.get("codename") or ""

            state_id = state_map.get(p_code)
            if not state_id:
                continue

            ward = existing_wards_by_code.get(w_code)
            if ward:
                ward.write({
                    "name": w_name,
                    "state_id": state_id,
                    "is_new": True,
                    "name_extension": w_codename,
                })
            else:
                wards_to_create.append({
                    "name": w_name,
                    "code": w_code,
                    "state_id": state_id,
                    "is_new": True,
                    "name_extension": w_codename,
                })

        chunk_size = 500
        for i in range(0, len(wards_to_create), chunk_size):
            Ward.create(wards_to_create[i:i + chunk_size])

        return True


class ResCountryWard(models.Model):
    _inherit = "res.country.ward"

    district_id = fields.Many2one(
        "res.country.district",
        string="District",
        required=False,
        ondelete="set null",
        index=True,
    )
    state_id = fields.Many2one(
        "res.country.state",
        string="Province / State",
        store=True,
        readonly=False,
        index=True,
    )
    is_new = fields.Boolean(string="Is Consolidated (NQ60)", default=False, copy=False)
    map_with_ward_ids = fields.Many2many(
        "res.country.ward",
        "res_country_ward_map_rel",
        "res_country_ward_id",
        "map_with_ward_id",
        string="Map With Legacy Wards",
        copy=False,
    )
    map_with_state_ids = fields.Many2many(
        "res.country.state",
        related="state_id.map_with_state_ids",
        string="Map With States",
    )

    def action_merge_ward_nq60(self):
        """Merge absorbed legacy wards into this consolidated ward and re-point partners."""
        self.ensure_one()
        if not self.map_with_ward_ids:
            return False
        absorbed = self.map_with_ward_ids
        partners = self.env["res.partner"].with_context(active_test=False).search([("ward_id", "in", absorbed.ids)])
        if partners:
            partners.write({
                "ward_id": self.id,
                "district_id": False,
            })
        absorbed.write({"active": False})
        return True

    @api.model
    def do_merge_ward_nq60(self):
        """Execute merger for all consolidated wards with map_with_ward_ids."""
        records = self.search([("map_with_ward_ids", "!=", False)])
        for ward in records:
            ward.action_merge_ward_nq60()
        return True
