# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class config_salary_insurence_union_dues(models.Model):
    _name = 'config.salary.insurence.union.dues'
    _description = 'Configure maximum salary for insurance/union dues'
    
    date_apply = fields.Date('Date Apply')
    rule_apply = fields.Many2one('hr.payslip.input.type','Rule Apply')
    maximum_amount = fields.Float('Maximum Amount')
