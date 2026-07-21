from odoo import api, fields, models


class ExcelReportColumn(models.Model):
    _name = "excel.report.column"
    _description = "Excel Report Column"
    _order = "sequence,create_date,id"

    name = fields.Char(string="Name", required=True)
    report_id = fields.Many2one('excel.report', required=True)
    model_id = fields.Many2one('ir.model', related='report_id.model_id', string="Model", store=True, readonly=True)
    model_name = fields.Char(related='model_id.model', string="Model Name", store=True, readonly=True)
    field = fields.Char(string="Field", required=True, help="Field name in the model. Ex: 'name', 'partner_id.name', etc.")
    sequence = fields.Integer(string="Sequence")
    width = fields.Integer(string="Width", help="Width of the column in Excel (in characters)", default=10)
    group = fields.Char(string="Group")
    merge_row = fields.Boolean(string="Merge Row", default=False)
    merge_col = fields.Boolean(string="Merge Column", default=False, compute="_compute_merge_col", store=True)
    function_id = fields.Many2one('excel.report.function', string="Function")
    format_id = fields.Many2one('excel.report.format', string="Format")

    @api.depends('group')
    def _compute_merge_col(self):
        for rec in self:
            rec.merge_col = bool(rec.group)

    def _get_field(self, record):
        """ Returns the field object for the column's field. """
        self.ensure_one()
        model = self.env[self.model_name]
        func_default = self.env['excel.report.function'].search([('name', '=', 'safe_value')], limit=1)
        func_default.execute()
        field_path = self.field.split('.')
        field_obj = model._fields.get(field_path[0])
        for part in field_path[1:]:
            if not field_obj or not hasattr(field_obj, 'related'):
                return None
            related_model = self.env[field_obj.related_model]
            field_obj = related_model._fields.get(part)
        return field_obj
