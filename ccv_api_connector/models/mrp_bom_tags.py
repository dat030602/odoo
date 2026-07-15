from platform import machine
from odoo import models, fields, api
import logging
import requests
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import json

_logger = logging.getLogger(__name__)

class MrpBomTags(models.Model):
    _name = "mrp.bom.tags"

    name = fields.Char(string="Tên tag")
    code = fields.Char(string="Mã tag")
    