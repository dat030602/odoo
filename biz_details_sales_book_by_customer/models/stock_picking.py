# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_actual_return_with_invoice = fields.Boolean("Is Actual Return With invoice")
    