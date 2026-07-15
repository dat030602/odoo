# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = "res.company"
    
    remove_supplier_reports = fields.Boolean(
        string="Remove Supplier Reports",
        help="If checked, reports including suppliers will be removed."
    )