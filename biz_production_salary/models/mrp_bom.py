# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    unit_price_cal_out_worker = fields.Float('Unit price for calculating output for workers', digits=(16, 0))
