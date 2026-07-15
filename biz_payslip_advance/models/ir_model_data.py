# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class IrModelData(models.Model):
    _inherit = "ir.model.data"
    
    def init(self):
        rules = ['ir_rule_hr_payslip_input_type_multi_company']
        noupdate_ids = self.search([('name', 'in', rules),('noupdate','=',True)])
        for data in noupdate_ids:
            data.noupdate = False