from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ccv_secondary_label(models.Model):
    _name = 'ccv.secondary.label'
    
    name = fields.Char('Tên')
    is_default = fields.Boolean('Mặc định', default=False)
