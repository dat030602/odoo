from odoo import api, fields, models


class ExcelReportColumn(models.Model):
    _name = "excel.report.column"
    _description = "Excel Report Column"

    name = fields.Char(string="Name", required=True)
    report_id = fields.Many2one('excel.report', required=True)
    model_id = fields.Many2one('ir.model', related='report_id.model_id', string="Model", store=True, readonly=True)
    model_name = fields.Char(related='model_id.model', string="Model Name", store=True, readonly=True)
    field_id = fields.Many2one('ir.model.fields', string="Field", domain="[('model', '=', model_name)]")
    sequence = fields.Integer(string="Sequence")
    width = fields.Integer(string="Width")
    group = fields.Char(string="Group")
    merge_row = fields.Boolean(string="Merge Row", default=False)
    merge_col = fields.Boolean(string="Merge Column", default=False)
    function_id = fields.Many2one('excel.report.function', string="Function")
    format_id = fields.Many2one('excel.report.format', string="Format")
