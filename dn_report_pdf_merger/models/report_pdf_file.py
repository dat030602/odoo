import base64
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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
    datas = fields.Binary(
        string='PDF File',
        required=True,
        attachment=True,
    )
    position = fields.Selection(
        [
            ('prepend', 'Cover (Beginning of Report)'),
            ('append', 'Appendix (End of Report)'),
        ],
        string='Position',
        required=True,
    )
    name = fields.Char(
        string='File Name',
        required=True,
        help='The name of the PDF file to be merged with the report.',
    )

    @api.constrains('datas')
    def _check_pdf_file(self):
        for record in self:
            if record.datas:
                try:
                    file_content = base64.b64decode(record.datas)
                except Exception:
                    raise ValidationError(_('Invalid file data.'))

                if not file_content.startswith(b'%PDF-'):
                    raise ValidationError(_('Invalid file format. Only valid PDF files are allowed.'))
