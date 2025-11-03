from odoo import models, fields
from psycopg2.extras import Json
import requests

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    address_type = fields.Selection([('before', 'Before Update'), ('after', 'After Update')], string='Address Type', default='before', config_parameter='vn_address_base.address_type', required=True)
