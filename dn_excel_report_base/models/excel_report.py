from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ExcelReport(models.AbstractModel):
    _name = "excel.report"
    _description = "Excel Report Base"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    technical_name = fields.Char(string="Technical Name", required=True, tracking=True, help="Technical name in the format 'module_name.report_name'")
    model_id = fields.Many2one('ir.model', string="Model", required=True, tracking=True)
    column_ids = fields.One2many('excel.report.column', 'report_id', string='Columns')
    signature_ids = fields.One2many('excel.report.signature', 'report_id', string='Signatures')
    state = fields.Selection(string="State", selection=[('draft', 'Draft'), ('confirmed', 'Confirmed')], default='draft', tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)

    report_action = fields.Many2one('ir.actions.report', string="Report Action", readonly=True, copy=False)

    @api.constrains('technical_name')
    def _check_technical_name(self):
        for report in self:
            if '.' not in report.technical_name:
                msg = "Technical Name must be in the format 'module_name.report_name'."
                raise ValidationError(msg)
            module_name, report_name = report.technical_name.split('.', 1)
            if not module_name or not report_name:
                msg = "Technical Name must be in the format 'module_name.report_name'."
                raise ValidationError(msg)
            if not self.env['ir.module.module'].search([('name', '=', module_name), ('state', '=', 'installed')]):
                msg = f"Module '{module_name}' is not installed."
                raise ValidationError(msg)
