# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    unit_price_cal_out_worker = fields.Float('Unit price for calculating output for workers', digits=(16, 0))
    unit_price_export = fields.Float('Unit price export', digits=(16, 0))
    unit_price_import = fields.Float('Unit price import', digits=(16, 0))
