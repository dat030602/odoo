# -*- coding: utf-8 -*-
import json

import requests

from odoo import models, fields
from odoo.exceptions import UserError

DEFAULT_HEADER = {
    'Accept': 'application/json',
    'Content-Type': 'application/json; charset=utf-8'
}


class ViettelSInvoiceType(models.Model):
    _name = 'viettel.sinvoice.type'
    _description = 'Viettel S-Invoice Type'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    description = fields.Char(string='Description')
