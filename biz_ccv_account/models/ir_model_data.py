# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.misc import formatLang
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare

from odoo.addons import decimal_precision as dp


class IrModelData(models.Model):
    _inherit = "ir.model.data"

    def init(self):
        rules = ['res_partner_rule_private_employee', 'res_partner_rule','sale_order_personal_rule', 'crm_rule_personal_lead', 'res_partner_rule_private_group',
                 'crm_rule_all_lead', 'sale_order_see_all', 'sale_order_report_personal_rule', 'sale_order_report_see_all'
                 ]
        noupdate_ids = self.search([('name', 'in', rules), ('noupdate', '=', True)])
        for data in noupdate_ids:
            data.noupdate = False