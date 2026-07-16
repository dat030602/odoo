from odoo import api, fields, models


class ExcelReportSignature(models.AbstractModel):
    _name = "excel.report.signature"
    _description = "Excel Report Signature"

    name = fields.Char(string="Name", required=True)
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user)
    fixed_text = fields.Text(string="Fixed Text")
    report_id = fields.Many2one('excel.report', required=True)
