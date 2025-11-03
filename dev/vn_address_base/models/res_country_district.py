from odoo import models, fields
import requests

class ResCountryDistrict(models.Model):
    _name = 'res.country.district'
    _description = 'District'
    _order = 'code'

    name = fields.Char('District name')
    code = fields.Char(string='Code', required=True)
    state_id = fields.Many2one('res.country.state', string='State', ondelete='cascade', store=True)
    country_id = fields.Many2one('res.country', string='Country', related='state_id.country_id', ondelete='cascade', store=True)
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
    ward_ids = fields.One2many('res.country.ward', 'district_id')

    def _sync_district_from_api(self, url):
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

