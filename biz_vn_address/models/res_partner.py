# -*- coding: utf-8 -*-

from ast import literal_eval
from operator import itemgetter
import time

from odoo import api, fields, models, _

# ADDRESS_FIELDS_VN = ('street', 'street2', 'wards_name', 'district_name', 'city', 'zip', 'country_id')

class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    
    city = fields.Char(string="City")
    def _default_country(self):
        country = self.env.ref('base.vn', False)
        return country and country.id or False
    
    def _get_full_address_vi(self):
        for res in self:
            address = res.street or ""
            address += res.wards_id and "%s%s"%(address == "" and "" or ", ",str(res.wards_id.name)) or ""
            address += res.district_id and "%s%s"%(address == "" and "" or ", ",str(res.district_id.name)) or ""
            address += res.state_id and "%s%s"%(address == "" and "" or ", ",str(res.state_id.name)) or ""
            res.full_address_vi = address
            
    full_address_vi = fields.Char('Address', compute=_get_full_address_vi)
    country_id = fields.Many2one('res.country',tracking=True, string='Country', ondelete='restrict', default=_default_country)
    district_id = fields.Many2one('res.country.district', 'District')
    wards_id = fields.Many2one('res.country.wards', 'Wards')
    contact_type = fields.Selection([('customer', 'Customer'),('supplier', 'Supplier')], string="Customers/Suppliers")
    
    @api.model
    def _get_address_format(self):
        # return self.country_id.address_format or self._get_default_address_format()
        return "%(street)s\n%(country_name)s\n%(state_name)s %(state_code)s\n%(district_name)s\n%(wards_name)s"

    def _display_address(self, without_company=False):
        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        # get the information that will be injected into the display format
        # get the address format

        address_format = self._get_address_format()
        args = {
            'state_code': self.state_id.code or '',
            'wards_name': self.wards_id.name or '',
            'district_name': self.district_id.name or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name(),
            'company_name': self.commercial_company_name or '',
        }
        for field in self._formatting_address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        
        # custom address for other module
        address_format, args = self.custom_display_address(address_format, args)

        return address_format % args

    def custom_display_address(self, address_format, args):
        return address_format, args

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        if self.parent_id:
            if self.parent_id.customer_rank > 0:
                self.contact_type = 'customer'
            else: self.contact_type = False
        else: self.contact_type = False
        return super(ResPartner, self).onchange_parent_id()
        
        