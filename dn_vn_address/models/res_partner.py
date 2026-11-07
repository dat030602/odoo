# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    district_id = fields.Many2one(
        "res.country.district",
        string="District",
        domain="[('state_id', '=?', state_id)]",
    )
    ward_id = fields.Many2one(
        "res.country.ward",
        string="Ward",
        domain="[('district_id', '=?', district_id)]",
    )
    full_address_vi = fields.Char(
        string="Full Address (VN)",
        compute="_compute_full_address_vi",
        store=True,
    )

    @api.depends("street", "ward_id.name", "district_id.name", "state_id.name", "country_id.name")
    def _compute_full_address_vi(self):
        for partner in self:
            parts = [
                partner.street,
                partner.ward_id.name,
                partner.district_id.name,
                partner.state_id.name,
                partner.country_id.name,
            ]
            partner.full_address_vi = ", ".join([p.strip() for p in parts if p and p.strip()])

    def _address_fields(self):
        return super()._address_fields() + ["district_id", "ward_id"]

    def _display_address_depends(self):
        return super()._display_address_depends() + ["district_id.name", "ward_id.name"]

    def _prepare_display_address(self, without_company=False):
        address_format, args = super()._prepare_display_address(without_company=without_company)
        args["district_name"] = self.district_id.name or ""
        args["ward_name"] = self.ward_id.name or ""
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

    @api.onchange("district_id")
    def _onchange_district_id(self):
        if self.district_id:
            if self.district_id.state_id:
                self.state_id = self.district_id.state_id
            if self.state_id and self.state_id.country_id:
                self.country_id = self.state_id.country_id
            if self.ward_id and self.ward_id.district_id != self.district_id:
                self.ward_id = False
        else:
            if self.ward_id:
                self.ward_id = False

    @api.onchange("state_id")
    def _onchange_state_id(self):
        if self.state_id:
            if self.state_id.country_id:
                self.country_id = self.state_id.country_id
            if self.district_id and self.district_id.state_id != self.state_id:
                self.district_id = False
                self.ward_id = False
        else:
            self.district_id = False
            self.ward_id = False

    @api.onchange("country_id")
    def _onchange_country_id(self):
        if self.country_id and self.state_id and self.state_id.country_id != self.country_id:
            self.state_id = False
            self.district_id = False
            self.ward_id = False
