from odoo import models, fields, api

class PayslipReportMapping(models.Model):
    _name = 'payslip.report.mapping'
    _description = 'Payslip Report Mapping'
    _order = 'custom_sequence'

    struct_id = fields.Many2one('hr.payroll.structure', string='Cấu trúc lương', required=True)
    rule_id = fields.Many2one('hr.salary.rule', string='Quy tắc gốc')
    code = fields.Char(string='Mã quy tắc (nếu không dùng ID)')
    custom_name = fields.Char(string='Tên hiển thị báo cáo', required=True)
    custom_sequence = fields.Integer(string='Thứ tự in', required=True, default=0)
