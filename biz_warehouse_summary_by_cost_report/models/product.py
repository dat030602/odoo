# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, SUPERUSER_ID, _

class ProductTemplate(models.Model):
    _inherit = "product.template"

    thcp_object_id = fields.Many2one('account.analytic.account','THCP object')