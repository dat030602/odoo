# -*- coding: utf-8 -*-
"""HTTP Controller for delivering rendered Excel template reports or ZIP archives."""

import datetime
import io
import logging
import re
import zipfile

from odoo import http, _
from odoo.http import request, content_disposition
from odoo.exceptions import AccessError, UserError
from odoo.tools import safe_eval

try:
    from ..services.parser import TemplateError
except ImportError:
    try:
        from services.parser import TemplateError
    except ImportError:
        TemplateError = UserError

_logger = logging.getLogger(__name__)

INVALID_FILENAME_CHARS = re.compile(r'[\\/*?:"<>|%]')


def sanitize_filename(name):
    """Sanitize string to produce a safe filesystem filename."""
    clean = INVALID_FILENAME_CHARS.sub('_', str(name or 'report')).strip()
    return clean or 'report'


class ExcelTemplateReportController(http.Controller):

    @http.route(
        '/excel_template_report/download',
        type='http',
        auth='user',
        methods=['GET', 'POST'],
    )
    def download(self, template_id=None, res_ids=None, **kw):
        """Generate and stream single Excel file or zip bundle for multiple records."""
        template_id = template_id or kw.get('template_id')
        res_ids = res_ids or kw.get('res_ids')

        template_obj = request.env['excel.report.template']
        try:
            template = template_obj.browse(int(template_id)).exists()
        except (ValueError, TypeError):
            raise UserError(_('Invalid template ID.'))

        if not template:
            raise UserError(_('Report template not found.'))

        template.check_access('read')

        user = request.env.user
        user_groups = getattr(user, 'group_ids', getattr(user, 'groups_id', None))
        if template.group_ids and user_groups and not (template.group_ids & user_groups):
            raise AccessError(_('You do not have permission to print this report.'))

        try:
            if isinstance(res_ids, int):
                ids = [res_ids]
            elif isinstance(res_ids, (list, tuple)):
                ids = [int(i) for i in res_ids if i]
            elif isinstance(res_ids, str):
                ids = [int(i.strip()) for i in res_ids.split(',') if i.strip()]
            elif res_ids:
                ids = [int(res_ids)]
            else:
                ids = []
        except (ValueError, TypeError):
            raise UserError(_('Invalid record IDs specified.'))

        if not ids:
            raise UserError(_('No records selected for printing.'))

        records = request.env[template.model].browse(ids).exists()
        if not records:
            raise UserError(_('Selected records could not be found.'))

        records.check_access('read')

        eval_dt = getattr(safe_eval, 'datetime', datetime)

        # Single record export
        if len(records) == 1:
            record = records[0]
            try:
                xlsx_content = template.render_record(record, strict=False)
            except TemplateError as te:
                raise UserError(str(te))

            filename_base = f"{sanitize_filename(template.name)}_{record.id}"
            if template.filename_expr:
                try:
                    eval_ctx = {
                        'record': record,
                        'company': getattr(record, 'company_id', False) or request.env.company,
                        'user': request.env.user,
                        'datetime': eval_dt,
                    }
                    custom_name = safe_eval.safe_eval(template.filename_expr, eval_ctx)
                    if custom_name:
                        filename_base = sanitize_filename(custom_name)
                except Exception as e:
                    _logger.warning("Failed to evaluate filename_expr for template %s: %s", template.id, e)

            if filename_base.lower().endswith('.xlsx'):
                filename = filename_base
            else:
                filename = f"{filename_base}.xlsx"

            return request.make_response(
                xlsx_content,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', content_disposition(filename)),
                ],
            )

        # Multi-record export (ZIP archive)
        zip_buffer = io.BytesIO()
        used_names = set()
        with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for record in records:
                try:
                    xlsx_content = template.render_record(record, strict=False)
                except TemplateError as te:
                    raise UserError(str(te))

                base_name = f"{sanitize_filename(template.name)}_{record.id}"
                if template.filename_expr:
                    try:
                        eval_ctx = {
                            'record': record,
                            'company': getattr(record, 'company_id', False) or request.env.company,
                            'user': request.env.user,
                            'datetime': eval_dt,
                        }
                        custom_name = safe_eval.safe_eval(template.filename_expr, eval_ctx)
                        if custom_name:
                            base_name = sanitize_filename(custom_name)
                    except Exception as e:
                        _logger.warning("Filename evaluation error: %s", e)

                if base_name.lower().endswith('.xlsx'):
                    base_name = base_name[:-5]

                candidate_name = f"{base_name}.xlsx"
                suffix = 2
                while candidate_name.lower() in used_names:
                    candidate_name = f"{base_name}_{suffix}.xlsx"
                    suffix += 1

                used_names.add(candidate_name.lower())
                zf.writestr(candidate_name, xlsx_content)

        zip_filename = f"{sanitize_filename(template.name)}_export.zip"
        return request.make_response(
            zip_buffer.getvalue(),
            headers=[
                ('Content-Type', 'application/zip'),
                ('Content-Disposition', content_disposition(zip_filename)),
            ],
        )
