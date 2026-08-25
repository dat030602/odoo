from odoo import models, fields


class ReportPdfFile(models.Model):
    _name = 'ir.actions.report.pdf.file'
    _description = 'Report PDF Merge Files'
    _order = 'sequence, id'

    sequence = fields.Integer('Sequence', default=10)
    report_id = fields.Many2one(
        'ir.actions.report',
        string='Report',
        ondelete='cascade',
        required=True,
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='PDF File',
        required=True,
        domain="[('mimetype', '=', 'application/pdf')]",
    )
    position = fields.Selection(
        [
            ('prepend', 'Cover (Beginning of Report)'),
            ('append', 'Appendix (End of Report)'),
        ],
        string='Position',
        required=True,
    )
