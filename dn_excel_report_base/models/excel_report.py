from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ExcelReport(models.Model):
    _name = "excel.report"
    _description = "Excel Report Base"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    technical_name = fields.Char(string="Technical Name", required=True, tracking=True, help="Technical name in the format 'module_name.report_name'")
    model_id = fields.Many2one('ir.model', string="Model", required=True, tracking=True, help="The model on which this report is based.", ondelete='cascade')
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

    @api.onchange('technical_name')
    def _onchange_technical_name(self):
        for rec in self:
            if rec.report_action:
                rec.report_action.report_name = rec.technical_name
    
    @api.onchange('name')
    def _onchange_name(self):
        for rec in self:
            if rec.report_action:
                rec.report_action.name = rec.name

    def action_create_report_action(self):
        for report in self:
            if report.report_action:
                continue

            report_action = self.env['ir.actions.report'].create({
                'name': report.name,
                'model': report.model_id.model,
                'report_type': 'xlsx',
                'report_name': report.technical_name,
                'binding_model_id': report.model_id.id,
                'binding_type': 'report',
            })
            report.report_action = report_action
