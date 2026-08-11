from odoo import fields, models


class ExcelReportDefinitionField(models.Model):
    _name = 'excel.report.definition.field'
    _description = 'Excel Report Definition Field'

    definition_id = fields.Many2one(
        'excel.report.definition',
        required=True,
        ondelete='cascade',
    )

    field_label = fields.Char(required=True)
    field_technical_name = fields.Char(required=True)
    field_type = fields.Selection([
        ('char', 'Text'),
        ('text', 'Long Text'),
        ('integer', 'Integer'),
        ('float', 'Decimal'),
        ('boolean', 'Checkbox'),
        ('date', 'Date'),
        ('datetime', 'Datetime'),
        ('many2one', 'Many2one'),
        ('selection', 'Selection'),
    ], required=True, default='char')

    relation_model_id = fields.Many2one(
        'ir.model',
        string='Relation Model',
        help='Required for Many2one fields.',
    )
    selection_value_text = fields.Text(
        string='Selection Values',
        help='One value per line as key:Label.',
    )
    required = fields.Boolean()
