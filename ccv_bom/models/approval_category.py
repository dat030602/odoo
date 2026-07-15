from odoo import models, fields, api
from bs4 import BeautifulSoup
import logging
import datetime
import pytz

_logger = logging.getLogger(__name__)

class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    has_count_norm = fields.Selection(selection=[
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Định mức chỉ may', default='no')

    has_fuel_norm = fields.Selection(selection=[
        ('optional', 'Tùy chọn'),
        ('no', 'Không'),
    ], string='Định mức xăng dầu', default='no')
