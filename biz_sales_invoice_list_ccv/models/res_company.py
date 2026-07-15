# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = "res.company"
    
    remove_customer_reports_ccv = fields.Boolean(
        string="Remove Customer Reports CCV",
        help="If checked, reports including customer will be removed."
    )