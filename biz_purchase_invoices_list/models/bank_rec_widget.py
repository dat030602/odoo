# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    product_id = fields.Many2one('product.template','Product')