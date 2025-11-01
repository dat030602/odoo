# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo import exceptions


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    partner_address = fields.Char('Address', compute='_compute_partner_address')

    def _compute_partner_address(self):
        for p in self:
            street = p.street or ''
            city = p.city or ''
            state = p.state_id.name or ''
            p.partner_address = ', '.join([el for el in [street, city, state] if el != ''])