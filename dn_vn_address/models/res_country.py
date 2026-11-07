# -*- coding: utf-8 -*-
import json
import logging
import urllib.request
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCountry(models.Model):
    _inherit = "res.country"

    @api.constrains("address_format")
    def _check_address_format(self):
        for record in self:
            if record.address_format:
                address_fields = self.env["res.partner"]._formatting_address_fields() + [
                    "state_code", "state_name", "country_code", "country_name", "company_name",
                    "district_name", "ward_name", "wards_name",
                ]
                try:
                    record.address_format % {i: 1 for i in address_fields}
                except (ValueError, KeyError):
                    raise UserError(_("The layout contains an invalid format key"))


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    active = fields.Boolean(string="Active", default=True)
    vn_code = fields.Integer(string="VN Administrative Code", index=True)
    name_extension = fields.Char(string="Name Extension", index=True)
    district_ids = fields.One2many("res.country.district", "state_id", string="Districts")

    def action_sync_provinces_v1(self):
        """Fetch and sync provinces, districts, and wards from Open API v1."""
        self._sync_addresses_v1()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Sync Completed"),
                "message": _("Vietnam administrative divisions (v1) have been synchronized successfully."),
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def _cron_sync_addresses_v1(self):
        """Cron entry point for syncing Vietnam administrative units."""
        return self._sync_addresses_v1()

    @api.model
    def _fetch_api_json(self, url, timeout=30):
        """Fetch JSON data from API endpoint."""
        req = urllib.request.Request(url, headers={"User-Agent": "Odoo-DN-VN-Address/19.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            _logger.error("Failed to fetch address data from %s: %s", url, str(e))
            raise UserError(_("Failed to fetch data from %s: %s") % (url, str(e)))

    @api.model
    def _sync_addresses_v1(self):
        """Fetch and batch-sync provinces, districts, and wards from Open API v1."""
        base_url = self.env["ir.config_parameter"].sudo().get_param(
            "dn_vn_address.api_url", "https://provinces.open-api.vn/api/v1"
        ).rstrip("/")

        vn = self.env.ref("base.vn", raise_if_not_found=False)
        if not vn:
            vn = self.env["res.country"].search([("code", "=", "VN")], limit=1)
        if not vn:
            raise UserError(_("Country Vietnam (code VN) not found."))

        # 1. Sync Provinces (/p/)
        provinces_url = f"{base_url}/p/"
        provinces = self._fetch_api_json(provinces_url)
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
                if state.name != p_name or state.vn_code != p_code or (state.name_extension or "") != p_codename:
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

        # Re-fetch state lookup
        state_map = {
            s.vn_code: s.id for s in self.search([("country_id", "=", vn.id), ("vn_code", "!=", False)])
        }

        # 2. Sync Districts (/d/)
        districts_url = f"{base_url}/d/"
        try:
            districts = self._fetch_api_json(districts_url)
        except Exception as e:
            _logger.warning("Could not sync districts: %s", str(e))
            districts = []

        District = self.env["res.country.district"]
        existing_districts = {
            (d.state_id.id, str(d.code)): d for d in District.search([])
        }

        districts_to_create = []
        for d in districts:
            d_code = str(d.get("code"))
            d_name = d.get("name")
            p_code = d.get("province_code")
            d_codename = d.get("codename") or ""

            state_id = state_map.get(p_code)
            if not state_id:
                continue

            key = (state_id, d_code)
            district = existing_districts.get(key)
            if district:
                if district.name != d_name or (district.name_extension or "") != d_codename:
                    district.write({
                        "name": d_name,
                        "name_extension": d_codename,
                    })
            else:
                districts_to_create.append({
                    "name": d_name,
                    "code": d_code,
                    "state_id": state_id,
                    "name_extension": d_codename,
                })

        if districts_to_create:
            District.create(districts_to_create)

        # 3. Sync Wards (/w/)
        wards_url = f"{base_url}/w/"
        try:
            wards = self._fetch_api_json(wards_url)
        except Exception as e:
            _logger.warning("Could not sync wards: %s", str(e))
            wards = []

        district_map = {
            d.code: d.id for d in District.search([])
        }
        Ward = self.env["res.country.ward"]
        existing_wards = {
            (w.district_id.id, str(w.code)): w for w in Ward.search([])
        }

        wards_to_create = []
        for w in wards:
            w_code = str(w.get("code"))
            w_name = w.get("name")
            d_code = str(w.get("district_code"))
            w_codename = w.get("codename") or ""

            district_id = district_map.get(d_code)
            if not district_id:
                continue

            key = (district_id, w_code)
            ward = existing_wards.get(key)
            if ward:
                if ward.name != w_name or (ward.name_extension or "") != w_codename:
                    ward.write({
                        "name": w_name,
                        "name_extension": w_codename,
                    })
            else:
                wards_to_create.append({
                    "name": w_name,
                    "code": w_code,
                    "district_id": district_id,
                    "name_extension": w_codename,
                })

        chunk_size = 500
        for i in range(0, len(wards_to_create), chunk_size):
            Ward.create(wards_to_create[i:i + chunk_size])

        return True


class ResCountryDistrict(models.Model):
    _name = "res.country.district"
    _description = "Vietnam Administrative District"
    _order = "name"

    name = fields.Char(string="District Name", required=True, index=True)
    code = fields.Char(string="District Code", required=True, index=True)
    state_id = fields.Many2one(
        "res.country.state",
        string="Province / State",
        required=True,
        ondelete="cascade",
        index=True,
    )
    ward_ids = fields.One2many("res.country.ward", "district_id", string="Wards")
    name_extension = fields.Char(string="Name Extension", index=True)
    active = fields.Boolean(string="Active", default=True)

    _uniq_district_code_state = models.Constraint(
        "unique(state_id, code)",
        "District code must be unique per province/state!",
    )


class ResCountryWard(models.Model):
    _name = "res.country.ward"
    _description = "Vietnam Administrative Ward / Commune"
    _order = "name"

    name = fields.Char(string="Ward Name", required=True, index=True)
    code = fields.Char(string="Ward Code", required=True, index=True)
    district_id = fields.Many2one(
        "res.country.district",
        string="District",
        required=True,
        ondelete="cascade",
        index=True,
    )
    state_id = fields.Many2one(
        "res.country.state",
        string="Province / State",
        related="district_id.state_id",
        store=True,
        readonly=False,
        index=True,
    )
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        default=lambda self: self.env.ref("base.vn", raise_if_not_found=False),
    )
    name_extension = fields.Char(string="Name Extension", index=True)
    active = fields.Boolean(string="Active", default=True)

    _uniq_ward_code_district = models.Constraint(
        "unique(district_id, code)",
        "Ward code must be unique per district!",
    )
