# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression
from datetime import timedelta, datetime, time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import json

class AverageCapitalPriceEndPeriod(models.Model):
    _inherit = "average.capital.price.end.period"

    
class AverageCapitalPriceEndPeriodLine(models.Model):
    _inherit = "average.capital.price.end.period.line"

    is_priority_th2 = fields.Boolean("Is Priority Th2", copy=False)

    