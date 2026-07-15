from platform import machine
from odoo import models, fields, api
import logging
import requests
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import json

_logger = logging.getLogger(__name__)

class MrpBom(models.Model):
    _inherit = "mrp.bom"

    tag_ids = fields.Many2many('mrp.bom.tags', string="Thẻ")
    