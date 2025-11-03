# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api


class Partner(models.Model):
    _inherit = 'res.partner'

    district_id = fields.Many2one(comodel_name='res.country.district', string='District', domain="[('state_id','=', state_id)]")
    ward_id = fields.Many2one(comodel_name='res.country.ward', string='Ward', domain="[('district_id', '=', district_id)]")
    vi_full_address = fields.Char(string='Vietnam Address', compute='_compute_vi_full_address')
    address_type = fields.Selection([('before', 'Before Update'), ('after', 'After Update')], string='Address Type', compute='_compute_address_type')

    @api.depends()
    def _compute_address_type(self):
        config_value = self.env['ir.config_parameter'].sudo().get_param('vn_address_base.address_type', 'before')
        for record in self:
            record.address_type = config_value

    @staticmethod
    def replace_address_name(pattern, name):
        for long_text, short_text in pattern.items():
            name = re.sub(long_text, short_text, name, flags=re.IGNORECASE)
        return name
    
    @staticmethod
    def replace_province_text(name):
        return re.sub(r'\btp\s+', '', name, flags=re.IGNORECASE)

    @api.depends('street', 'ward_id', 'district_id', 'state_id')
    def _compute_vi_full_address(self):
        for record in self:
            address = []
            if record.street:
                address.append(record.street)
            if record.ward_id:
                address.append(record.ward_id.name)
            if record.district_id:
                address.append(record.district_id.name)
            if record.state_id:
                address.append(record.state_id.name)
            record.vi_full_address = ', '.join(address)
