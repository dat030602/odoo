import re
from odoo import models, fields


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
    ], string='Division Type')
