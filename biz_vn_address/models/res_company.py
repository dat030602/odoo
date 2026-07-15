# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ResCompany(models.Model):
    _inherit = "res.company"
    
    def _default_country(self):
        return self.env.ref('base.vn').id
    
    state_id = fields.Many2one('res.country.state', compute='_compute_address', inverse='_inverse_state', string="Fed. State")
    district_id = fields.Many2one('res.country.district', compute='_compute_address', inverse='_inverse_district', string="Fed. District")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', default=_default_country)
    wards_id = fields.Many2one('res.country.wards', 'Wards')
    
    def _compute_address(self):
        for company in self.filtered(lambda company: company.partner_id):
            address_data = company.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = company.partner_id.browse(address_data['contact']).sudo()
                company.street = partner.street
                company.street2 = partner.street2
                company.city = partner.city
                company.zip = partner.zip
                company.state_id = partner.state_id
                company.district_id = partner.district_id
                company.country_id = partner.country_id
#                 company.fax = partner.fax
                
    def _inverse_state(self):
        for company in self:
            company.partner_id.state_id = company.state_id
            
    def _inverse_district(self):
        for company in self:
            company.partner_id.district_id = company.district_id


    @api.onchange('country_id')
    def on_change_country_id(self):
        domain = {}
        if self.country_id:
            self.state_id = False
            self.district_id = False
            self.wards_id = False
            domain['state_id'] = [('country_id', '=', self.country_id.id)]
            domain['district_id'] = [('state_id', '=', False)]
            domain['wards_id'] = [('state_id', '=', False)]
        return {'domain': domain}
    
    @api.onchange('state_id')
    def on_change_state_id(self):
        domain = {}
        if self.state_id:
            self.district_id = False
            self.wards_id = False
            domain['district_id'] = [('state_id', '=', self.state_id.id)]
            domain['wards_id'] = [('state_id', '=', self.state_id.id)]
        return {'domain': domain}
    
    @api.onchange('district_id')
    def on_change_district_id(self):
        domain = {}
        if self.district_id:
            self.state_id = self.district_id.state_id and self.district_id.state_id.id or False
            self.wards_id = False
            domain['wards_id'] = [('district_id', '=', self.district_id.id)]
        return {'domain': domain}
    
    @api.onchange('wards_id')
    def on_change_wards_id(self):
        if self.wards_id:
            self.district_id = self.wards_id.district_id and self.wards_id.district_id.id or False
            self.state_id = self.wards_id.state_id and self.wards_id.state_id.id or False
        return {}
