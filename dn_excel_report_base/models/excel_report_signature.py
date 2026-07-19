from odoo import api, fields, models


class ExcelReportSignature(models.AbstractModel):
    _name = "excel.report.signature"
    _description = "Excel Report Signature"

    name = fields.Char(string="Name", required=True)
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user)
    fixed_text = fields.Text(string="Fixed Text")
    report_id = fields.Many2one('excel.report', required=True)
    is_readonly = fields.Boolean(string="Show Signature", compute="_compute_is_readonly", store=True)

    @api.depends('user_id', 'fixed_text')
    def _compute_is_readonly(self):
        for signature in self:
            if not signature.user_id:
                signature.is_readonly = True
            else:
                signature.is_readonly = False
