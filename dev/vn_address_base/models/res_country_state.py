from odoo import models, fields
import requests


class ResCountryState(models.Model):
    _inherit = 'res.country.state'
    _order = 'code'

    phone_code = fields.Integer(string='Phone Code')
    code_number = fields.Integer(string='Code Number')
    division_type = fields.Selection([
        ("tỉnh", "Tỉnh"),
        ("thành phố trung ương", "Thành phố trung ương"),
        ("huyện", "Huyện"),
        ("quận", "Quận"),
        ("thành phố", "Thành phố"),
        ("thị xã", "Thị xã"),
        ("xã", "Xã"),
        ("thị trấn", "Thị trấn"),
        ("phường", "Phường"),
        ("đặc khu", "Đặc khu"),
    ], string='Division Type')

    def _sync_province_from_api(self, url, country_id):
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
                    'country_id': country_id,
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
