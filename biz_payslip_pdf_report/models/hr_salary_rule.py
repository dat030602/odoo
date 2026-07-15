from odoo import fields, models, api
import re

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'


    payslip_no = fields.Integer('Sequence number')
    is_bold = fields.Boolean('Is bold PDF?')
    index_display = fields.Char('Table of contents displayed')
    unit = fields.Char('Unit')
    is_display_title = fields.Boolean('Is display title?')
    config_a_category = fields.Boolean('Check', compute='compute_config_a_category', store=True, readonly=False)

    @api.depends('index_display')
    def compute_config_a_category(self):
        for rec in self:
            rec.config_a_category = False
            if rec.index_display:
                pattern = r"A\.[1-9]$|A\.10$"
                if re.search(pattern, str(rec.index_display)):
                    rec.config_a_category = True



