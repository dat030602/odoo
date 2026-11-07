# -*- coding: utf-8 -*-
"""Excel Report Template model."""

import base64
import datetime
from decimal import Decimal
import io
import logging
import time
import zipfile

import openpyxl

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

try:
    from odoo.tools.safe_eval import safe_eval, datetime as safe_datetime, time as safe_time
except ImportError:
    safe_eval = None
    safe_datetime = datetime
    safe_time = time

try:
    from ..services.parser import scan_sheet, TemplateError
    from ..services.renderer import render_template
    from ..services.resolver import normalize_html, resolve_path, to_cell_value
except ImportError:
    from services.parser import scan_sheet, TemplateError
    from services.renderer import render_template
    from services.resolver import normalize_html, resolve_path, to_cell_value

_logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

DEFAULT_PYTHON_CODE = '''# Python Script Mode for Excel Report Template
# Available Context:
#   record: Current record (e.g. sale.order, purchase.order)
#   records: Current recordset (for batch print)
#   company: Company record (record.company_id or env.company)
#   env: Odoo environment
#   user: Current user (env.user)
#   datetime, date, time, Decimal: Python standard libraries
#   format_date(date_val, fmt=None): Format date using user lang or fmt
#   format_datetime(dt_val, fmt=None): Format datetime using user lang or fmt
#   format_amount(amount, currency=None): Format monetary amount
#   html2plaintext(html_text): Convert HTML string to clean plain text
#   to_cell_value(val): Convert Odoo field values to Excel compatible types
#   resolve_path(record, path): Safely resolve dotted path on record
#   _dynamic_import(module_name): Import a module from the configured whitelist
#   allowed_modules: Dictionary of modules enabled in Excel Report Module Settings
#
# Return Data:
# 1. Scalar variables for ${var_name}:
#    variables['tax_included'] = 'Yes' if record.amount_tax > 0 else 'No'
#
# 2. Table rows for ${table:summary.field}:
#    tables['summary'] = [
#        {
#            'item': idx,
#            'product': line.name,
#            'qty': line.product_qty,
#            'price': line.price_unit,
#        }
#        for idx, line in enumerate(record.order_line, start=1)
#    ]
'''


def execute_render_record(template_record, record, strict=False):
    template_bytes = base64.b64decode(template_record.template_file)
    return render_template(
        template_bytes,
        record=record,
        template=template_record,
        empty_policy=template_record.empty_table_policy,
        strict=strict,
    )


class ExcelReportTemplate(models.Model):
    _name = 'excel.report.template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Excel Report Template'
    _order = 'name, id'

    name = fields.Char(string='Template Name', required=True, tracking=True)
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        index=True,
    )
    model = fields.Char(
        related='model_id.model',
        string='Model Tech Name',
        readonly=True,
        store=True,
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        readonly=True,
        store=True,
    )
    template_file = fields.Binary(
        string='Template File (.xlsx)',
        required=True,
        attachment=True,
    )
    template_filename = fields.Char(string='File Name')
    filename_expr = fields.Char(
        string='Export Filename Expression',
        default="'%s_%s' % (record._name.replace('.', '_'), record.id)",
        help="Python expression evaluating filename without extension. Variables: 'record', 'company', 'datetime'",
    )
    empty_table_policy = fields.Selection(
        [
            ('keep_blank', 'Keep 1 Blank Row'),
            ('remove', 'Remove Row'),
        ],
        string='Empty Table Policy',
        default='keep_blank',
        required=True,
        help='Action taken when a table datasource yields 0 rows: keep the template row blank or delete the row.',
    )
    config_mode = fields.Selection(
        [
            ('builder', 'Visual Builder'),
            ('code', 'Python Code Script'),
        ],
        string='Configuration Mode',
        default='builder',
        required=True,
        tracking=True,
        help='Choose between visual variables/datasources builder or custom Python script execution.',
    )
    python_code = fields.Text(
        string='Python Code Script',
        default=DEFAULT_PYTHON_CODE,
        help='Custom Python script to compute template variables and table datasets dynamically.',
    )
    group_ids = fields.Many2many(
        'res.groups',
        'excel_report_template_group_rel',
        'template_id',
        'group_id',
        string='Allowed Groups',
        help='If empty, all internal users with read access to the record can print this report.',
    )
    variable_ids = fields.One2many(
        'excel.report.variable',
        'template_id',
        string='Variables',
        copy=True,
    )
    datasource_ids = fields.One2many(
        'excel.report.datasource',
        'template_id',
        string='Data Sources',
        copy=True,
    )
    binding_action_id = fields.Many2one(
        'ir.actions.server',
        string='Binding Action',
        ondelete='set null',
        copy=False,
    )
    is_bound = fields.Boolean(
        string='Is Bound',
        compute='_compute_is_bound',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.name or _('New Template')

    @api.depends('binding_action_id')
    def _compute_is_bound(self):
        for rec in self:
            rec.is_bound = bool(rec.binding_action_id)

    @api.constrains('template_file', 'template_filename')
    def _check_template_file(self):
        for rec in self:
            if not rec.template_file:
                continue
            try:
                raw = base64.b64decode(rec.template_file)
            except Exception:
                raise ValidationError(_('Invalid template file: not a valid zip / Excel file.'))
            if len(raw) > MAX_FILE_SIZE:
                raise ValidationError(_('Template file size exceeds maximum permitted limit (10 MB).'))
            if rec.template_filename and rec.template_filename.lower().endswith('.xlsm'):
                raise ValidationError(_('Macro-enabled workbooks (.xlsm) are strictly rejected for security.'))
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                    namelist = zf.namelist()
                    if 'xl/workbook.xml' not in namelist:
                        raise ValidationError(_('Invalid template: file is not a valid OpenXML Excel workbook (.xlsx).'))
                    if 'xl/vbaProject.bin' in namelist:
                        raise ValidationError(_('Template file contains macros (vbaProject.bin), which are not allowed.'))
            except zipfile.BadZipFile:
                raise ValidationError(_('Invalid template file: not a valid zip / Excel file.'))

    def unlink(self):
        for rec in self:
            if rec.binding_action_id:
                rec.binding_action_id.unlink()
        return super().unlink()

    def action_bind_print_button(self):
        """Create or update server action to bind 'Print Excel' to target model's Print menu."""
        self.ensure_one()
        server_action_model = self.env['ir.actions.server']
        action_name = _('Print: %s') % self.name
        python_code = f"action = env['excel.report.template'].browse({self.id}).action_open_download(records.ids)"
        vals = {
            'name': action_name,
            'model_id': self.model_id.id,
            'binding_model_id': self.model_id.id,
            'binding_type': 'report',
            'binding_view_types': 'list,form',
            'state': 'code',
            'code': python_code,
        }
        if self.binding_action_id:
            self.binding_action_id.write(vals)
        else:
            action = server_action_model.create(vals)
            self.binding_action_id = action.id
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Print Action Bound'),
                'message': _("Successfully bound '%s' to the Print menu of %s.") % (self.name, self.model_id.name),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_unbind_print_button(self):
        """Remove sidebar action binding for this template."""
        self.ensure_one()
        if self.binding_action_id:
            self.binding_action_id.unlink()
            self.binding_action_id = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Print Action Removed'),
                'message': _("Successfully removed Print menu button for '%s'.") % self.name,
                'type': 'info',
                'sticky': False,
            }
        }

    def action_open_download(self, record_ids):
        """Action handler called by sidebar server action to route download."""
        self.ensure_one()
        user = self.env.user
        user_groups = getattr(user, 'group_ids', getattr(user, 'groups_id', None))
        if self.group_ids and user_groups and not (self.group_ids & user_groups):
            raise AccessError(_('You do not have permission to generate this report.'))
        res_ids_str = ','.join(str(i) for i in record_ids) if record_ids else ''
        return {
            'type': 'ir.actions.act_url',
            'url': f'/excel_template_report/download?template_id={self.id}&res_ids={res_ids_str}',
            'target': 'self',
        }

    def render_record(self, record, strict=False):
        """Render template for a given single record."""
        self.ensure_one()
        return execute_render_record(self, record, strict=strict)

    # -------------------------------------------------------------------------
    # Python Code Execution Context & Methods
    # -------------------------------------------------------------------------

    def _get_python_eval_context(self, record=None, records=None):
        """Provide rich eval context with utility libraries and helper functions,
        modeled after dn_bi_python_editor."""
        self.ensure_one()

        allowed_modules = self.env['excel.report.python.module']._get_allowed_modules()

        def _dynamic_import(module_name):
            if module_name not in allowed_modules:
                raise UserError(
                    _("Python module '%s' is not enabled in Excel Report Module Settings.")
                    % module_name
                )
            return allowed_modules[module_name]

        rec = record
        if rec is None and self.model:
            rec = self.env[self.model].search([], limit=1)
        recs = records if records is not None else rec

        env = self.env
        company = getattr(rec, 'company_id', None) or env.company
        user = env.user

        def _format_date(d, fmt=None):
            if not d:
                return ""
            try:
                from odoo.tools import format_date
                return format_date(env, d, date_format=fmt)
            except Exception:
                if hasattr(d, "strftime"):
                    return d.strftime(fmt or "%Y-%m-%d")
                return str(d)

        def _format_datetime(dt, fmt=None):
            if not dt:
                return ""
            try:
                from odoo.tools import format_datetime
                return format_datetime(env, dt, dt_format=fmt)
            except Exception:
                if hasattr(dt, "strftime"):
                    return dt.strftime(fmt or "%Y-%m-%d %H:%M:%S")
                return str(dt)

        def _format_amount(amt, curr=None):
            if amt is None:
                return ""
            currency = curr or getattr(rec, "currency_id", None)
            if currency:
                try:
                    from odoo.tools import format_amount
                    return format_amount(env, amt, currency)
                except Exception:
                    pass
            try:
                return f"{float(amt):,.2f}"
            except Exception:
                return str(amt)

        return {
            # Execution control & configured module imports
            '_dynamic_import': _dynamic_import,
            'allowed_modules': allowed_modules,
            # Standard Odoo environment
            'env': env,
            'user': user,
            'record': rec,
            'records': recs,
            'fields': rec,
            'company': company,
            # Standard python date/time & types
            'datetime': safe_datetime,
            'date': getattr(safe_datetime, 'date', datetime.date),
            'time': safe_time,
            'Decimal': Decimal,
            # Standard Python helpers
            'hasattr': hasattr,
            'isinstance': isinstance,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'min': min,
            'max': max,
            'sum': sum,
            'round': round,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sorted': sorted,
            'reversed': reversed,
            # Exceptions
            'Exception': Exception,
            'UserError': UserError,
            'ValueError': ValueError,
            'TypeError': TypeError,
            'KeyError': KeyError,
            # Built-in formatters and data helpers
            'format_date': _format_date,
            'format_datetime': _format_datetime,
            'format_amount': _format_amount,
            'html2plaintext': normalize_html,
            'to_cell_value': to_cell_value,
            'resolve_path': resolve_path,
            # Output containers to be populated by user code
            'variables': {},
            'tables': {},
            'result': None,
        }

    def _execute_python_request(self, record=None, records=None, for_check=False):
        """Execute Python code script and return computed variables and tables."""
        self.ensure_one()
        if not self.python_code or not self.python_code.strip():
            if for_check:
                raise UserError(_("Python Code cannot be empty when testing script execution."))
            return {'variables': {}, 'tables': {}}

        eval_context = self._get_python_eval_context(record=record, records=records)
        try:
            safe_eval(self.python_code, eval_context, mode="exec")

            computed_vars = dict(eval_context.get('variables') or {})
            computed_tables = dict(eval_context.get('tables') or {})
            res = eval_context.get('result')

            if isinstance(res, dict):
                if 'variables' in res and isinstance(res['variables'], dict):
                    computed_vars.update(res['variables'])
                if 'tables' in res and isinstance(res['tables'], dict):
                    computed_tables.update(res['tables'])

                for k, v in res.items():
                    if k in ('variables', 'tables'):
                        continue
                    if isinstance(v, (list, tuple)) and (not v or all(isinstance(row, (dict, object)) for row in v)):
                        computed_tables[k] = list(v)
                    elif hasattr(v, '_name'):  # Recordset
                        computed_tables[k] = list(v)
                    else:
                        computed_vars[k] = v

            # Validate tables structure
            for tbl_name, tbl_rows in computed_tables.items():
                if hasattr(tbl_rows, '_name'):
                    computed_tables[tbl_name] = list(tbl_rows)
                elif not isinstance(tbl_rows, (list, tuple)):
                    raise UserError(_("Table '%s' must be a list of row dictionaries or an Odoo recordset.") % tbl_name)

            return {
                'variables': computed_vars,
                'tables': computed_tables,
            }
        except Exception as e:
            _logger.exception("Python script execution error in template %s", self.name)
            raise UserError(_("Python script execution error:\n\n%s") % str(e)) from e

    def action_test_python_code(self):
        """Test execute python code against first record of model and report results."""
        self.ensure_one()
        rec = None
        if self.model:
            rec = self.env[self.model].search([], limit=1)
        if not rec:
            raise UserError(_("No record found in model '%s' to test Python script execution.") % (self.model_id.name or self.model))

        res = self._execute_python_request(record=rec, for_check=True)
        vars_found = list(res.get('variables', {}).keys())
        tables_found = {tbl: len(rows) for tbl, rows in res.get('tables', {}).items()}

        summary_lines = [
            _("Test execution on record '%s' (ID %s) succeeded!") % (rec.display_name or rec.id, rec.id),
            "",
            _("Computed Variables (%d): %s") % (len(vars_found), vars_found if vars_found else _("None")),
            _("Computed Tables (%d):") % len(tables_found),
        ]
        for tbl, count in tables_found.items():
            summary_lines.append(f"  • {tbl}: {count} rows")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Python Code Validation Succeeded'),
                'message': '\n'.join(summary_lines),
                'type': 'success',
                'sticky': True,
            }
        }

    def action_validate_template(self):
        """Validate template placeholders against defined variables and datasources."""
        self.ensure_one()
        if not self.template_file:
            raise UserError(_("Please upload a template file first."))
        raw = base64.b64decode(self.template_file)
        try:
            wb = openpyxl.load_workbook(io.BytesIO(raw))
        except Exception as e:
            raise UserError(_("Failed to load Excel workbook: %s") % str(e))

        defined_vars = {v.name for v in self.variable_ids if v.name}
        defined_datasources = {
            ds.name: {col.key for col in ds.column_ids if col.key}
            for ds in self.datasource_ids if ds.name
        }

        warnings = []

        # If in code mode, execute Python script on sample record to discover defined variables and tables
        if self.config_mode == 'code':
            sample_rec = None
            if self.model:
                sample_rec = self.env[self.model].search([], limit=1)
            try:
                py_res = self._execute_python_request(record=sample_rec, for_check=True)
                defined_vars.update(py_res.get('variables', {}).keys())
                for tbl_name, tbl_rows in py_res.get('tables', {}).items():
                    col_keys = set()
                    if tbl_rows:
                        first_row = tbl_rows[0]
                        if isinstance(first_row, dict):
                            col_keys.update(first_row.keys())
                    defined_datasources[tbl_name] = col_keys
            except Exception as e:
                warnings.append(_("Python script validation warning: %s") % str(e))

        for ws in wb.worksheets:
            try:
                scan = scan_sheet(ws)
            except TemplateError as te:
                raise UserError(str(te))
            for p in scan.cells:
                if p.kind == 'table':
                    if isinstance(p.expr, (tuple, list)):
                        ds_name = p.expr[0]
                        col_key = p.expr[1] if len(p.expr) > 1 else ''
                    else:
                        parts = str(p.expr).split('.')
                        ds_name = parts[0]
                        col_key = parts[1] if len(parts) > 1 else ''
                    if ds_name not in defined_datasources:
                        warnings.append(
                            _("Sheet '%s' Row %s: Unknown datasource '%s'") % (ws.title, p.row, ds_name)
                        )
                    elif col_key and defined_datasources[ds_name] and col_key not in defined_datasources[ds_name]:
                        warnings.append(
                            _("Sheet '%s' Row %s: Column '%s' not found in datasource '%s'") % (ws.title, p.row, col_key, ds_name)
                        )
                elif p.kind == 'expr':
                    if p.expr.startswith('fields.') or p.expr.startswith('company.'):
                        continue
                    root_ident = p.expr.split('.')[0].strip()
                    if root_ident not in defined_vars:
                        warnings.append(
                            _("Sheet '%s' Row %s: Variable or field '%s' is not defined.") % (ws.title, p.row, p.expr)
                        )

        if warnings:
            msg = '\n'.join(warnings[:10])
            if len(warnings) > 10:
                msg += f'\n...and {len(warnings) - 10} more.'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Template Validation Warnings'),
                    'message': msg,
                    'type': 'warning',
                    'sticky': True,
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Validation Passed'),
                'message': _('All placeholders and datasource references validated cleanly.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_test_print(self):
        """Test print action on the first record of the model."""
        self.ensure_one()
        record = self.env[self.model].search([], limit=1)
        if not record:
            raise UserError(_("No records found for model '%s' to test print.") % self.model)
        return self.action_open_download([record.id])
