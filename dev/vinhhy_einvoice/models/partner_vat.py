# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api, _
from odoo.osv import expression
from odoo.exceptions import UserError


class PartnerVAT(models.Model):
    _name = 'partner.vat'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Partner VAT'
    _order = "name asc"

    active = fields.Boolean(default=True)
    name = fields.Char('Name', index=True, required=True)
    partner_id = fields.Many2one('res.partner', string='Contact')
    ref = fields.Char(string='Reference', copy=False)
    street = fields.Char(string='Street')
    ward_id = fields.Many2one('res.ward', 'Ward')
    district_id = fields.Many2one('res.district', 'District')
    city_id = fields.Many2one('res.city', 'City ID')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',
        default=lambda self: self.env.ref('base.vn'))
    partner_address = fields.Char('Address', compute='_compute_partner_address')
    email = fields.Char(string='Email')
    vat = fields.Char('VAT')
    phone = fields.Char(string='Phone')
    # mobile = fields.Char(string='Mobile')
    company_type = fields.Selection(string='Company Type', selection=[('person', 'Individual'), ('company', 'Company')], default='person')

    def _compute_partner_address(self):
        for p in self:
            street = p.street or ''
            ward = p.ward_id.name or ''
            district = p.district_id.name or ''
            city = p.city_id.name or ''
            country = p.country_id.name or ''
            p.partner_address = ', '.join([el for el in [street, ward, district, city, country] if el != ''])
    
    # @api.constrains('ref')
    # def _check_duplicate_ref(self):
    #     for partner in self:
    #         if partner.ref and self.env['partner.vat'].search_count([('ref', '=', partner.ref)]) > 1:
    #             raise UserError(_('Duplicated Error: Reference "%s" is existed in other contact(s)!') % partner.ref)
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|','|','|','|', ('name', operator, name), ('partner_id.name', operator, name), ('ref', operator, name), \
                      ('email', operator, name), ('phone', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)