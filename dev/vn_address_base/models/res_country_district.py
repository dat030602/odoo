from odoo import models, fields


class ResCountryDistrict(models.Model):
    _name = 'res.country.district'
    _description = 'District'
    _order = 'code'

    name = fields.Char('District name')
    code = fields.Char(string='Code', required=True)
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country', related='state_id.country_id')
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
    ward_ids = fields.One2many('res.country.ward', 'district_id')
