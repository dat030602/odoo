from odoo import models, fields


class ResCountryWard(models.Model):
    _name = 'res.country.ward'
    _description = 'ward'
    _order = 'name'

    code = fields.Char(string='Ward Code')
    name = fields.Char(string='Ward name')
    district_id = fields.Many2one('res.country.district', string='District', domain="[('state_id', '=', state_id)]")
    state_id = fields.Many2one('res.country.state', 'State', domain="[('country_id', '=', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', related='district_id.country_id')
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
    ], string='Division Type')

