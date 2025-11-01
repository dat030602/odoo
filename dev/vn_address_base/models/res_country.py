from odoo import models, fields
from psycopg2.extras import Json
import requests

class ResCountry(models.Model):
    _inherit = 'res.country'

    address_type = fields.Selection([('before', 'Before Update'), ('after', 'After Update')], string='Address Type', default='before', required=True)

    def sync_address_base_from_api(self):
        """
        Update address base from API
        """
        self.ensure_one()
        url = 'https://provinces.open-api.vn/api'
        if self.address_type == 'before':
            sub = "/v1/p/"
            self._sync_province_from_api(url + sub)
            sub = "/v1/d/"
            self._sync_district_from_api(url + sub)
            sub = "/v1/w/"
            self._sync_ward_from_api(url + sub)
        elif self.address_type == 'after':
            sub = "/v2/p/"
            self._sync_province_from_api(url + sub)
            sub = "/v2/w/"
            self._sync_ward_from_api(url + sub)

    def _sync_province_from_api(self, url):
        self.ensure_one()
        response = requests.get(url)
        data = response.json()
        state_env = self.env['res.country.state']
        for item in data:
            state = state_env.search([('code_number', '=', item.get('code', 0)), ('code_number', '!=', 0)], limit=1)
            if not state:
                state_env.create({
                    'name': item.get('name', ''),
                    'code': item.get('codename', ''),
                    'code_number': item.get('code', 0),
                    'phone_code': item.get('phone_code', 0),
                    'country_id': self.id,
                    'division_type': item.get('division_type', ''),
                })
            else:
                state.write({
                     'name': item.get('name', ''),
                    'code': item.get('codename', ''),
                    'code_number': item.get('code', 0),
                    'phone_code': item.get('phone_code', 0),
                    'division_type': item.get('division_type', ''),
                })
        
    def _sync_district_from_api(self, url):
        self.ensure_one()
        response = requests.get(url)
        data = response.json()
        state_env = self.env['res.country.state']
        district_env = self.env['res.country.district']
        for item in data:
            district = district_env.search([('code_number', '=', item.get('code', 0)), ('code_number', '!=', 0)], limit=1)
            state = state_env.search([('code_number', '=', item.get('province_code', 0)), ('code_number', '!=', 0)], limit=1)
            if not district:
                district_env.create({
                    'name': item.get('name', ''),
                    'code': item.get('codename', ''),
                    'code_number': item.get('code', 0),
                    'phone_code': item.get('phone_code', 0),
                    'state_id': state.id,
                    'division_type': item.get('division_type', ''),
                })
            else:
                district.write({
                    'name': item.get('name', ''),
                    'code': item.get('codename', ''),
                    'code_number': item.get('code', 0),
                    'phone_code': item.get('phone_code', 0),
                    'state_id': state.id,
                    'division_type': item.get('division_type', ''),
                })

    def _sync_ward_from_api(self, url):
        self.ensure_one()
        response = requests.get(url)
        data = response.json()
        district_env = self.env['res.country.district']
        ward_env = self.env['res.country.ward']
        for item in data:
            ward = ward_env.search([('code_number', '=', item.get('code', 0)), ('code_number', '!=', 0)], limit=1)
            district = district_env.search([('code_number', '=', item.get('district_code', 0)), ('code_number', '!=', 0)], limit=1)
            if not ward:
                ward_env.create({
                    'name': item.get('name', ''),
                    'code': item.get('codename', ''),
                    'code_number': item.get('code', 0),
                    'phone_code': item.get('phone_code', 0),
                    'district_id': district.id,
                    'division_type': item.get('division_type', ''),
                })
            else:
                ward.write({
                    'name': item.get('name', ''),
                    'code': item.get('codename', ''),
                    'code_number': item.get('code', 0),
                    'phone_code': item.get('phone_code', 0),
                    'district_id': district.id,
                    'division_type': item.get('division_type', ''),
                })
