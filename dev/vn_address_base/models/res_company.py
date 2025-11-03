from odoo import models, fields, api
from psycopg2.extras import Json
import requests

class ResCompany(models.Model):
    _inherit = 'res.company'

    district_id = fields.Many2one('res.country.district', string='District', domain="[('state_id','=', state_id)]", ondelete='set null')
    ward_id = fields.Many2one('res.country.ward', string='Ward', domain="[('district_id', '=', district_id)]", ondelete='set null')
