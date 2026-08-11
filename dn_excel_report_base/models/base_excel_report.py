# -*- coding: utf-8 -*-
"""
base_excel_report.py
=====================

Core framework for template-based Excel report generation in Odoo.

Design Pattern:
---------------
    Template Method Pattern — This base class defines the algorithm skeleton.
    Child modules override Hook Methods to inject business-specific logic
    without touching the processing pipeline.

Template Design Contract:
--------------------------
    The Excel template file (.xlsx) stored in ir.attachment MUST follow
    these conventions:

    1. LOOP BLOCKS
       Use ``{% for x in path %}`` and ``{% endfor %}`` markers in the
       leftmost cell of their respective rows to define loop regions.
       The engine automatically inserts rows, copies styles, and resolves
       placeholders for each item.

    2. PLACEHOLDER SYNTAX
       Use ``{{ path.to.value }}`` anywhere in the sheet for dynamic values.
       Examples:
           {{ company.name }}  →  replaced with company name
           {{ print_date }}    →  replaced with formatted date string
           {{ lines | sum:'amount' }}  →  replaced with SUBTOTAL formula

    3. CONDITIONAL BLOCKS
       Use ``{% if expr %}`` and ``{% endif %}`` markers to conditionally
       include or exclude rows.

    4. AGGREGATE FILTERS
       Use ``{{ list_name | sum:'field' }}`` outside loop blocks to generate
       live Excel SUBTOTAL formulas.

Processing Pipeline (action_generate_excel):
---------------------------------------------
    Step 1  → _load_template()              : Fetch attachment, decode base64,
                                              load into BytesIO RAM buffer.
    Step 2  → _get_report_context() [HOOK]  : Child returns a dict with all
                                              data needed for rendering.
    Step 3  → TemplateEngine.render()       : Parse blocks, expand loops,
                                              resolve placeholders, generate
                                              SUBTOTAL formulas.
    Step 4  → _autofit_columns()            : Widen columns to fit data
                                              (Normal Mode only).
    Step 5  → _export_file()                : Save workbook → BytesIO → base64
                                              → wizard download state.

Performance Modes:
------------------
    Normal Mode  (records < FAST_MODE_THRESHOLD)
        • Full per-cell style copy from template row to inserted rows.
        • Column auto-fit after data write.

    Fast Mode    (records >= FAST_MODE_THRESHOLD)
        • Skips _copy_row_styles() → relies on column-level template formatting.
        • Skips _autofit_columns().

Module:     base_excel_report_v2
Model:      base.excel.report
Type:       TransientModel (Wizard)
Author:     Dat Nguyen
Version:    19.0.2.0.0
"""

import base64
import io
from copy import copy

import openpyxl
from openpyxl.utils import get_column_letter

from odoo import models, fields, _
from odoo.exceptions import UserError

from .template_engine import TemplateEngine, TemplateError


# ─────────────────────────────────────────────────────────────────────────────
# MODULE-LEVEL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

FAST_MODE_THRESHOLD = 1000
"""int: Record count at which the framework switches to Fast Mode.

    Tune this value based on your server hardware and acceptable response time.
    Typical safe range: 500–2000.
    Below threshold  → Full styling (border, font, fill, autofit).
    At/above threshold → Lean write (value + number_format only).
"""

MAX_COLUMN_WIDTH = 50
"""int: Upper bound for auto-fit column width (in Excel character units).

    Prevents a single cell containing a long paragraph from expanding
    a column to an unusable width. Users can manually adjust in Excel.
"""

COLUMN_WIDTH_FONT_FACTOR = 1.2
"""float: Multiplier applied to character count when calculating column width.

    Compensates for the fact that most fonts render characters wider than
    exactly 1 character unit. Calibri 11pt (Excel default) ≈ 1.15–1.25.
"""

COLUMN_WIDTH_PADDING = 2
"""int: Extra character units added to the calculated width for visual breathing room."""


# ─────────────────────────────────────────────────────────────────────────────
# BASE MODEL
# ─────────────────────────────────────────────────────────────────────────────

class BaseExcelReport(models.TransientModel):
    """
    Reusable base wizard for generating Excel reports from Odoo attachment templates.

    Inheritance Guide:
    ------------------
    Create a new TransientModel in your module and inherit this base::

        class MyReport(models.TransientModel):
            _name        = 'my.module.excel.report'
            _inherit     = 'base.excel.report'
            _description = 'My Custom Excel Report'

            # Add filter fields specific to your report
            date_from = fields.Date('From Date')
            date_to   = fields.Date('To Date')

    Then override the 2 required + 1 optional hook methods.
    The entire pipeline runs automatically when the user clicks
    "Generate Report" in the wizard.

    Required Hooks:
    ---------------
    * _get_template_name()     → str
    * _get_report_context()    → dict

    Optional Hooks:
    ---------------
    * _get_output_filename()   → str
    """

    _name = 'base.excel.report'
    _description = 'Base Excel Template Report (V2 Engine)'

    # ─────────────────────────────────────────────────────────────────────────
    # FIELDS
    # ─────────────────────────────────────────────────────────────────────────

    excel_file = fields.Binary(
        string='Excel File',
        readonly=True,
        help='Generated Excel file. Available after clicking "Generate Report".',
    )
    file_name = fields.Char(
        string='File Name',
        readonly=True,
        help='Name of the generated Excel file presented for download.',
    )
    state = fields.Selection(
        selection=[
            ('choose', 'Configure'),
            ('download', 'Download'),
        ],
        string='State',
        default='choose',
        help=(
            'configure: User sets report parameters.\n'
            'download: Report is ready; download widget is visible.'
        ),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # HOOK METHODS  ── Override these in child modules
    # ─────────────────────────────────────────────────────────────────────────

    def _get_template_name(self):
        """
        Return the exact filename of the Excel template in ir.attachment.

        The framework searches ir.attachment with domain
        ``[('name', '=', <returned_value>)]``.

        Returns:
            str: Filename including extension (e.g. ``'template_sale_report.xlsx'``).

        Raises:
            NotImplementedError: Always — must be overridden by child module.

        Child Example::

            def _get_template_name(self):
                return 'template_sale_report.xlsx'
        """
        raise NotImplementedError(
            f'[{self._name}] _get_template_name() must be implemented in the child module.'
        )

    def _get_report_context(self):
        """
        Return the report context as a dict.

        This is the single required hook for child modules. The returned dict
        is passed directly to ``TemplateEngine.render()`` and used to resolve
        all ``{{ }}`` placeholders and ``{% for %}`` / ``{% if %}`` blocks
        in the template.

        The dict can contain arbitrarily nested dicts, lists, and Odoo
        recordsets. The engine resolves dot-paths using ``dict.get`` first,
        then ``getattr``, so both plain dicts and Odoo records work
        transparently.

        Returns:
            dict: Arbitrarily nested dict containing all data needed for
                  template rendering.

        Raises:
            NotImplementedError: Always — must be overridden by child module.

        Child Example::

            def _get_report_context(self):
                orders = self.env['sale.order'].search(
                    [('state', 'in', ['sale', 'done'])],
                    order='date_order asc',
                )
                return {
                    'company': {'name': self.env.company.name},
                    'print_date': fields.Date.today().strftime('%d/%m/%Y'),
                    'lines': [
                        {
                            'name': o.name,
                            'date': o.date_order.date(),
                            'amount': o.amount_total,
                        }
                        for o in orders
                    ],
                }
        """
        raise NotImplementedError(
            f'[{self._name}] _get_report_context() must be implemented in the child module.'
        )

    def _get_output_filename(self, file_name=None):
        """
        Return the filename for the generated (output) Excel file.

        Override this in child modules to provide a more descriptive or
        date-stamped filename.

        Returns:
            str: Output filename including ``.xlsx`` extension.

        Default behavior:
            ``'template_sale_report.xlsx'`` → ``'sale_report_output.xlsx'``

        Child Example::

            def _get_output_filename(self, file_name=None):
                if file_name:
                    return file_name
                date_str = fields.Date.today().strftime('%Y%m%d')
                return f'Sale_Report_{date_str}.xlsx'
        """
        if file_name:
            template_name = file_name
        else:
            template_name = self._get_template_name()
        return (
            template_name
            .replace('template_', '', 1)
            .replace('.xlsx', '_output.xlsx')
        )

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC ACTION  ── Triggered by UI button
    # ─────────────────────────────────────────────────────────────────────────

    def action_generate_excel(self):
        """
        Orchestrate the full Excel report generation pipeline.

        This is the single public entry point called by the "Generate Report"
        button in the wizard view. It sequentially executes all pipeline
        steps and transitions the wizard to 'download' state on success.

        Steps:
            1. Load template from ir.attachment into RAM.
            2. Retrieve context dict via _get_report_context().
            3. Render template via TemplateEngine.render().
            4. [Normal Mode] Auto-fit column widths.
            5. Export workbook → base64 → wizard download field.

        Returns:
            dict: ``ir.actions.act_window`` action reloading the wizard form
                  with ``state='download'`` to expose the file download widget.

        Raises:
            UserError: Template not found / unreadable, context error,
                       template rendering error, or any unhandled exception.
        """
        self.ensure_one()

        # Step 1 ── Load template
        wb, sheet = self._load_template()

        # Step 2 ── Get context
        context = self._get_report_context()
        if not isinstance(context, dict):
            raise UserError(_(
                "_get_report_context() must return a dict, got %s."
            ) % type(context).__name__)

        # Step 3 ── Render template
        engine = TemplateEngine(sheet)
        try:
            engine.render(context)
        except TemplateError as exc:
            raise UserError(_(
                "Error rendering Excel template '%(tpl)s': %(err)s"
            ) % {'tpl': self._get_template_name(), 'err': str(exc)})

        # Step 4 ── Auto-fit columns (Normal Mode only)
        # Determine performance mode based on total expanded rows
        total_rows = sheet.max_row
        is_fast_mode = total_rows >= FAST_MODE_THRESHOLD
        if not is_fast_mode:
            self._autofit_columns(sheet, 1, sheet.max_row)

        # Step 5 ── Export
        return self._export_file(wb)

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE PIPELINE METHODS  ── Do NOT override in child modules
    # ─────────────────────────────────────────────────────────────────────────

    def _load_template(self):
        """
        Fetch the Excel template attachment and load it non-destructively into RAM.

        The template's base64-encoded binary data is decoded and wrapped in a
        ``BytesIO`` buffer. ``openpyxl`` reads from this in-memory buffer,
        leaving the original ir.attachment record completely untouched.
        Every report generation call starts from a clean copy of the template.

        Returns:
            tuple[openpyxl.Workbook, openpyxl.worksheet.worksheet.Worksheet]:
                ``(workbook, active_sheet)`` ready for read/write operations.

        Raises:
            UserError:
                * Template attachment not found by name.
                * File is not a valid .xlsx workbook (corrupt or wrong format).
        """
        template_name = self._get_template_name()

        attachment = self.env['ir.attachment'].search(
            [('name', '=', template_name)],
            limit=1,
        )
        if not attachment:
            raise UserError(
                f"Template file '{template_name}' was not found in Attachments.\n\n"
                "Please upload the template via:\n"
                "Settings → Technical → Database Structure → Attachments → Create\n\n"
                "Ensure the attachment Name matches exactly (case-sensitive)."
            )

        try:
            file_bytes = base64.b64decode(attachment.datas)
            virtual_file = io.BytesIO(file_bytes)
            wb = openpyxl.load_workbook(virtual_file)
            sheet = wb.active
        except Exception as exc:
            raise UserError(
                f"Failed to read the Excel template '{template_name}'.\n"
                f"Ensure the file is a valid .xlsx workbook.\n\n"
                f"Technical detail: {exc}"
            ) from exc

        return wb, sheet

    def _autofit_columns(self, sheet, start_row, end_row):
        """
        Widen each column to accommodate the longest content within the data rows.

        Called in Normal Mode only. Scans only the data row range (start_row
        to end_row) to avoid inflating column widths due to long report title
        text in the Header area above the table.

        Width calculation per column:
            max_chars     = max character count across all data cells in column
            raw_width     = (max_chars × COLUMN_WIDTH_FONT_FACTOR) + COLUMN_WIDTH_PADDING
            applied_width = min(raw_width, MAX_COLUMN_WIDTH)

        The calculated width is applied only if it exceeds the column's current
        width defined in the template. This ensures that manually set column
        widths in the template are respected and never narrowed.

        Args:
            sheet: Active worksheet.
            start_row: First data row (1-based).
            end_row: Last data row (1-based).

        Notes:
            * Multi-line cell values (containing ``'\\n'``) are handled by measuring
              the longest individual line segment.
            * ``openpyxl.utils.get_column_letter()`` converts column index to letter
              for use with ``sheet.column_dimensions``.
        """
        for col_idx in range(1, sheet.max_column + 1):
            col_letter = get_column_letter(col_idx)
            max_length = 0

            for row_idx in range(start_row, end_row + 1):
                cell_value = sheet.cell(row=row_idx, column=col_idx).value

                if cell_value is None:
                    continue

                # Handle multi-line cells gracefully
                longest_line = max(
                    len(line)
                    for line in str(cell_value).split('\n')
                )
                max_length = max(max_length, longest_line)

            if max_length == 0:
                continue

            new_width = min((max_length * COLUMN_WIDTH_FONT_FACTOR) + COLUMN_WIDTH_PADDING, MAX_COLUMN_WIDTH)

            # Respect template's manually set column widths — only widen, never narrow
            current_width = sheet.column_dimensions[col_letter].width or 0
            if new_width > current_width:
                sheet.column_dimensions[col_letter].width = new_width

    def _export_file(self, wb, file_name=None):
        """
        Serialize the populated workbook to base64 and expose it for download.

        Saves the workbook into a fresh ``BytesIO`` buffer (separate from the
        input buffer, so the original template bytes are never overwritten).
        Encodes the buffer contents to base64 and writes to the ``excel_file``
        Binary field. Transitions the wizard state to ``'download'``.

        Args:
            wb: Fully populated workbook ready for export.
            file_name: The name of the file to be generated.

        Returns:
            dict: ``ir.actions.act_window`` action to reload the current wizard
                  record in a new popup window, now showing the download widget.
        """
        output_buffer = io.BytesIO()
        wb.save(output_buffer)
        output_buffer.seek(0)

        self.write({
            'excel_file': base64.b64encode(output_buffer.read()),
            'file_name': self._get_output_filename(file_name=file_name),
            'state': 'download',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Server Action Integration (Section 14)
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_from_attachment(self, name, attachment, context):
        """Render an Excel template attachment against a context dict.

        This is the shared entry point for both the hook-based wizard flow
        (via ``action_generate_excel``) and the Server Action flow
        (via ``ir.actions.server._run_action_excel_template_multi``).

        Args:
            name: The name of the Excel template.
            attachment: An ``ir.attachment`` record holding a .xlsx template.
            context: A plain dict with all data needed for template rendering.

        Returns:
            dict: ``ir.actions.act_window`` action to reload the wizard form
                  with ``state='download'`` to expose the file download widget.

        Raises:
            UserError: If the template cannot be read or rendering fails.
        """
        self.ensure_one()
        try:
            data = base64.b64decode(attachment)
            workbook = openpyxl.load_workbook(io.BytesIO(data))
        except Exception as exc:
            raise UserError(_(
                "Failed to read the Excel template '%(name)s': %(err)s"
            ) % {'name': name, 'err': str(exc)})

        sheet = workbook.active
        engine = TemplateEngine(sheet)
        try:
            engine.render(context)
        except TemplateError as exc:
            raise UserError(_(
                "Error rendering Excel template '%(tpl)s': %(err)s"
            ) % {'tpl': name, 'err': str(exc)})

        return self._export_file(workbook, file_name=name)
