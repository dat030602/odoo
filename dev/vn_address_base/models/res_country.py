from odoo import models, fields
from psycopg2.extras import Json
import requests

class ResCountry(models.Model):
    _inherit = 'res.country'

    def sync_address_base_from_api(self):
        """
        Update address base from API
        """
        config_env = self.env['ir.config_parameter'].sudo().get_param('vn_address_base.address_type', 'before')
        url = 'https://provinces.open-api.vn/api'
        if config_env == 'before':
            sub = "/v1/p/"
            self.env['res.country.state']._sync_province_from_api(url + sub, self.id)
            sub = "/v1/d/"
            self.env['res.country.district']._sync_district_from_api(url + sub)
            sub = "/v1/w/"
            self.env['res.country.ward']._sync_ward_from_api(url + sub)
        else:
            sub = "/v2/p/"
            self.env['res.country.state']._sync_province_from_api(url + sub, self.id)
            sub = "/v2/w/"
            self.env['res.country.district']._sync_district_from_api(url + sub)
