from odoo import models, fields, api
import logging
from datetime import datetime
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResPartenr(models.Model):
    _inherit = "res.partner"

    contract_number = fields.Char(string='Số hợp đồng')
