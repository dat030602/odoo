from odoo import fields, models, api


class HrSalaryRuleCategory(models.Model):
    _inherit = 'hr.salary.rule.category'


    print_payslip = fields.Boolean('Print payslip')
    print_scale = fields.Boolean('Print scale')

