from odoo import models, fields, api
from bs4 import BeautifulSoup
import logging
import datetime
import pytz

_logger = logging.getLogger(__name__)

class EnterDailyWorkOutputOther(models.Model):
    _inherit = 'enter.daily.work.output.other'

    approval_id = fields.Many2one('approval.request')
    