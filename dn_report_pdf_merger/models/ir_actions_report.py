import base64
import logging

from odoo import models, fields, api
from odoo.tools.pdf import merge_pdf

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    prepend_file_ids = fields.One2many(
        'ir.actions.report.pdf.file',
        'report_id',
        string='Prepend PDF Files',
        domain=[('position', '=', 'prepend')],
    )
    append_file_ids = fields.One2many(
        'ir.actions.report.pdf.file',
        'report_id',
        string='Append PDF Files',
        domain=[('position', '=', 'append')],
    )

    @api.model
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """Override to merge additional PDF files into the generated report.

        Workflow:
        1. Call super() to generate the original report PDF content.
        2. If the report has configured prepend or append files, collect all
           PDF streams in the correct order:
           [prepend files (sorted by sequence)] + [original report] +
           [append files (sorted by sequence)]
        3. Merge all streams using Odoo's built-in merge_pdf tool.
        4. Return the merged content, falling back to the original on error.
        """
        content, ext = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        report = self._get_report_from_name(report_ref)
        if report.report_type != 'qweb-pdf':
            return content, ext

        prepends = report.prepend_file_ids
        appends = report.append_file_ids

        if not prepends and not appends:
            return content, ext

        streams = []

        # Add prepend files (cover pages) sorted by sequence
        for pdf_file in prepends:
            if pdf_file.attachment_id.datas:
                streams.append(base64.b64decode(pdf_file.attachment_id.datas))

        # Add the original report PDF
        streams.append(content)

        # Add append files (appendix pages) sorted by sequence
        for pdf_file in appends:
            if pdf_file.attachment_id.datas:
                streams.append(base64.b64decode(pdf_file.attachment_id.datas))

        try:
            merged_content = merge_pdf(streams)
            return merged_content, ext
        except Exception as e:
            _logger.warning(
                "Failed to merge PDF files for report '%s': %s. "
                "Returning original report content.",
                report_ref,
                e,
            )
            return content, ext
