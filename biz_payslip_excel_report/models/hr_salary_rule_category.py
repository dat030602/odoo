# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _


class HrSalaryRuleCategory(models.Model):
    _inherit = 'hr.salary.rule.category'
    
    is_receivables = fields.Boolean('Receivables')

