from odoo import fields, models, api


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    code_tncn = fields.Char('Social insurance')
    code_bhxh = fields.Char('Personal income')
    pdf_password = fields.Char("PDF Password")
    
class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    code_tncn = fields.Char('Social insurance')
    code_bhxh = fields.Char('Personal income')
    pdf_password = fields.Char("PDF Password")
