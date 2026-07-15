from odoo import models, fields, api
import logging
import json
from datetime import datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = "res.partner"

    abbreviation = fields.Char(string="Tên viết tắt")

    