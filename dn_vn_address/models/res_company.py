# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    district_id = fields.Many2one(
        "res.country.district",
        string="District",
        compute="_compute_address",
        inverse="_inverse_district",
    )
    ward_id = fields.Many2one(
        "res.country.ward",
        string="Ward",
        compute="_compute_address",
        inverse="_inverse_ward",
    )

    def _get_company_address_field_names(self):
        return super()._get_company_address_field_names() + ["district_id", "ward_id"]

    def _inverse_district(self):
        for company in self:
            company.partner_id.district_id = company.district_id

    def _inverse_ward(self):
        for company in self:
            company.partner_id.ward_id = company.ward_id

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
