# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    ward_id = fields.Many2one(
        "res.country.ward",
        string="Ward",
        domain="[('state_id', '=?', state_id)]",
    )

    @api.depends("street", "ward_id.name", "district_id.name", "state_id.name", "country_id.name")
    def _compute_full_address_vi(self):
        for partner in self:
            parts = [
                partner.street,
                partner.ward_id.name,
                partner.district_id.name if partner.district_id else None,
                partner.state_id.name,
                partner.country_id.name,
            ]
            partner.full_address_vi = ", ".join([p.strip() for p in parts if p and p.strip()])

    def _prepare_display_address(self, without_company=False):
        address_format, args = super()._prepare_display_address(without_company=without_company)
        args["ward_name"] = self.ward_id.name or ""
        if self.district_id:
            args["district_name"] = self.district_id.name or ""
            if "%(district_name)s" not in address_format and "%(ward_name)s" in address_format:
                address_format = address_format.replace("%(ward_name)s", "%(ward_name)s, %(district_name)s")
        else:
            args["district_name"] = ""
            if "%(district_name)s" in address_format:
                address_format = address_format.replace(", %(district_name)s", "").replace("%(district_name)s", "")
        return address_format, args

    @api.onchange("ward_id")
    def _onchange_ward_id(self):
        if self.ward_id:
            if self.ward_id.district_id:
                self.district_id = self.ward_id.district_id
            if self.ward_id.state_id:
                self.state_id = self.ward_id.state_id
            elif self.district_id and self.district_id.state_id:
                self.state_id = self.district_id.state_id
            if self.state_id and self.state_id.country_id:
                self.country_id = self.state_id.country_id

    @api.onchange("state_id")
    def _onchange_state_id(self):
        if self.state_id:
            if self.state_id.country_id:
                self.country_id = self.state_id.country_id
            if self.district_id and self.district_id.state_id != self.state_id:
                self.district_id = False
            if self.ward_id and self.ward_id.state_id != self.state_id:
                self.ward_id = False
        else:
            self.district_id = False
            self.ward_id = False
