from odoo import models, fields, api
import requests
import json
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    vinhhy_einv_username = fields.Char('E-Invoice Username')
    vinhhy_einv_password = fields.Char('E-Invoice Password')
