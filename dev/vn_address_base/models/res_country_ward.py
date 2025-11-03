from odoo import models, fields
import requests

class ResCountryWard(models.Model):
    _name = 'res.country.ward'
    _description = 'ward'
    _order = 'name'

    code = fields.Char(string='Ward Code')
    name = fields.Char(string='Ward name')
    district_id = fields.Many2one('res.country.district', string='District', domain="[('state_id', '=', state_id)]", ondelete='cascade')
    state_id = fields.Many2one('res.country.state', 'State', related='district_id.state_id', store=True)
    country_id = fields.Many2one('res.country', string='Country', related='state_id.country_id', store=True)
    phone_code = fields.Integer(string='Phone Code')
    code_number = fields.Integer(string='Code Number')
    division_type = fields.Selection([
        ("tỉnh", "Tỉnh"),
        ("thành phố trung ương", "Thành phố Trung Ương"),
        ("huyện", "Huyện"),
        ("quận", "Quận"),
        ("thành phố", "Thành phố"),
        ("thị xã", "Thị Xã"),
        ("xã", "Xã"),
        ("thị trấn", "Thị Trấn"),
        ("phường", "Phường"),
        ("đặc khu", "Đặc khu"),
    ], string='Division Type')

    def _sync_ward_from_api(self, url):
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
