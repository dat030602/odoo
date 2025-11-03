from odoo import models, fields
from psycopg2.extras import Json
import requests

class ResCompany(models.Model):
    _inherit = 'res.company'

    district_id = fields.Many2one('res.country.district', string='District', domain="[('state_id','=', state_id)]")
    ward_id = fields.Many2one('res.country.ward', string='Ward', domain="[('district_id', '=', district_id)]")
