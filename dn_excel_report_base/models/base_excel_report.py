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

    1. TABLE MARKER
       Place the string ``<TABLE_START>`` in the leftmost cell of the first
       data row of the table. This cell marks where row insertion begins.
       The row containing this marker acts as the style template for all
       inserted rows (Normal Mode).

    2. PLACEHOLDER SYNTAX
       Use ``{{KEY}}`` anywhere in the sheet for dynamic values.
       Examples:
           {{COMPANY_NAME}}  →  replaced with company name
           {{PRINT_DATE}}    →  replaced with formatted date string
           {{GRAND_TOTAL}}   →  replaced with an Excel SUBTOTAL formula

    3. GRAND TOTAL ROW
       Place a Grand Total row BELOW the ``<TABLE_START>`` row in the
       template. Use a placeholder (e.g. ``{{GRAND_TOTAL}}``) in the
       amount cell. The framework pushes this row down automatically
       when rows are inserted, preserving its relative position.

    4. COLUMN-LEVEL FORMATTING (Fast Mode)
       For reports with large datasets, format entire columns (A, B, C…)
       directly in Excel instead of individual cells. The framework
       applies column-level formatting to all inserted rows automatically,
       bypassing the need for per-cell style copy in Python.

Processing Pipeline (action_generate_excel):
---------------------------------------------
    Step 1  → _load_template()              : Fetch attachment, decode base64,
                                              load into BytesIO RAM buffer.
    Step 2  → _find_table_marker()          : Scan sheet for <TABLE_START>,
                                              return (row, col) coordinates.
    Step 3  → _get_report_data()  [HOOK]    : Child returns dataset
                                              (Recordset or list of dicts).
    Step 4  → insert_rows() + style copy    : Insert blank rows; copy styles
                                              from template row (Normal Mode).
    Step 5  → _write_table_data() [HOOK]    : Child maps data → Excel cells.
    Step 6  → _get_header_footer_data() [HOOK] : Child returns placeholder map.
              _replace_placeholders()       : Scan and replace all markers.
    Step 7  → _autofit_columns()            : Widen columns to fit data
                                              (Normal Mode only).
    Step 8  → _export_file()                : Save workbook → BytesIO → base64
                                              → wizard download state.

Performance Modes:
------------------
    Normal Mode  (records < FAST_MODE_THRESHOLD)
        • Full per-cell style copy from template row to inserted rows.
        • Column auto-fit after data write.

    Fast Mode    (records >= FAST_MODE_THRESHOLD)
        • Skips _copy_row_styles() → relies on column-level template formatting.
        • Skips _autofit_columns().
        • Per-cell number_format assignment in _write_table_data() is still
          safe and recommended (string assignment, negligible CPU cost).

Module:     base_excel_report
Model:      base.excel.report
Type:       TransientModel (Wizard)
Author:     Your Company
Version:    16.0.1.0.0
"""

import base64
import io
from copy  import copy

import openpyxl
from openpyxl.utils import get_column_letter

from odoo              import models, fields
from odoo.exceptions   import UserError


# ─────────────────────────────────────────────────────────────────────────────
# MODULE-LEVEL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

TABLE_START_MARKER = "<TABLE_START>"
"""str: Marker string placed in the Excel template to identify the first data row.

    The cell containing this exact string (stripped of surrounding whitespace)
    is treated as (row=R, col=C) — the insertion anchor for all table rows.
    After data is written, the marker string is overwritten by the first
    data value in that cell.
"""

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

    Then override the 3 required + 1 optional hook methods.
    The entire pipeline runs automatically when the user clicks
    "Generate Report" in the wizard.

    Required Hooks:
    ---------------
    * _get_template_name()     → str
    * _get_report_data()       → Recordset | list[dict]
    * _write_table_data(sheet, data, start_row, start_col)

    Optional Hooks:
    ---------------
    * _get_header_footer_data(start_row, end_row, start_col) → dict
    * _get_output_filename()   → str
    """

    _name        = 'base.excel.report'
    _description = 'Base Excel Template Report'

    # ─────────────────────────────────────────────────────────────────────────
    # FIELDS
    # ─────────────────────────────────────────────────────────────────────────

    excel_file = fields.Binary(
        string   = 'Excel File',
        readonly = True,
        help     = 'Generated Excel file. Available after clicking "Generate Report".',
    )
    file_name = fields.Char(
        string   = 'File Name',
        readonly = True,
        help     = 'Name of the generated Excel file presented for download.',
    )
    state = fields.Selection(
        selection = [
            ('choose',   'Configure'),
            ('download', 'Download'),
        ],
        string  = 'State',
        default = 'choose',
        help    = (
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

    def _get_report_data(self):
        """
        Return the dataset to be rendered into the Excel table.

        Each element in the returned collection represents exactly ONE
        physical row that will be inserted into the Excel sheet.

        Return Formats:
        ---------------
        **Flat report** — Return an Odoo Recordset::

            return self.env['sale.order'].search([('state', '=', 'done')])

        **Grouped report** — Return a list of dicts with a ``row_type`` key.
        Each dict must have ``'row_type': 'data'`` or ``'row_type': 'subtotal'``.
        The framework inserts ``len(result)`` rows total, so subtotal rows
        count toward the insertion count::

            lines = []
            for rec in records:
                lines.append({'row_type': 'data', 'record': rec})
            lines.append({'row_type': 'subtotal', 'label': 'Subtotal', 'group_key': ...})
            return lines

        Returns:
            Recordset | list[dict]:
                Collection whose ``len()`` equals the total rows to insert.

        Raises:
            NotImplementedError: Always — must be overridden by child module.
        """
        raise NotImplementedError(
            f'[{self._name}] _get_report_data() must be implemented in the child module.'
        )

    def _write_table_data(self, sheet, data, start_row, start_col):
        """
        Write dataset values into the worksheet at the given coordinates.

        Called AFTER rows have been inserted (and styled in Normal Mode).
        The child module defines which data field maps to which Excel column.

        Args:
            sheet     (openpyxl.worksheet.worksheet.Worksheet):
                        Active worksheet. Use ``sheet.cell(row, col).value = x``
                        to assign values. Use ``sheet.cell(row, col).number_format``
                        to apply display formatting (safe in both modes).
            data      (Recordset | list[dict]):
                        Exactly what _get_report_data() returned.
            start_row (int): 1-based row index of the first data row.
            start_col (int): 1-based column index of the <TABLE_START> cell.

        Raises:
            NotImplementedError: Always — must be overridden by child module.

        Child Example (flat)::

            def _write_table_data(self, sheet, data, start_row, start_col):
                FORMAT_NUMBER = '#,##0.00'
                FORMAT_DATE   = 'DD/MM/YYYY'
                for idx, rec in enumerate(data):
                    row = start_row + idx
                    sheet.cell(row=row, column=start_col    ).value = rec.name
                    date_cell = sheet.cell(row=row, column=start_col + 1)
                    date_cell.value         = rec.date_order.date()
                    date_cell.number_format = FORMAT_DATE
                    amt_cell = sheet.cell(row=row, column=start_col + 2)
                    amt_cell.value         = rec.amount_total
                    amt_cell.number_format = FORMAT_NUMBER

        Child Example (grouped with subtotals) — see module docstring for full pattern.
        """
        raise NotImplementedError(
            f'[{self._name}] _write_table_data() must be implemented in the child module.'
        )

    def _get_header_footer_data(self, start_row, end_row, start_col):
        """
        Return a mapping of placeholder strings to replacement values.

        Called AFTER table data is written, so ``start_row`` and ``end_row``
        reflect the final positions of data rows in the output sheet.
        This allows building accurate Excel formula strings such as
        ``=SUBTOTAL(9, C10:C250)``.

        The framework performs a full-sheet scan and replaces any cell whose
        string value contains a placeholder key. Replacement is applied even
        if the key is embedded within a longer string.

        Args:
            start_row (int): 1-based index of the first data row (after insertion).
            end_row   (int): 1-based index of the last data row (after insertion).
            start_col (int): 1-based column index of the <TABLE_START> marker.

        Returns:
            dict[str, str]:
                Keys are placeholder strings (e.g. ``'{{DATE}}'``).
                Values are replacement strings.
                Return an Excel formula string (starting with ``'='``) to
                insert a live formula into the cell.
                Return ``{}`` (default) if no replacements are needed.

        Child Example::

            def _get_header_footer_data(self, start_row, end_row, start_col):
                amount_col = get_column_letter(start_col + 2)   # e.g. 'D'
                return {
                    '{{COMPANY_NAME}}': self.env.company.name,
                    '{{PRINT_DATE}}'  : fields.Date.today().strftime('%d/%m/%Y'),
                    '{{CREATOR}}'     : self.env.user.name,
                    '{{GRAND_TOTAL}}' : f'=SUBTOTAL(9,{amount_col}{start_row}:{amount_col}{end_row})',
                }
        """
        return {}

    def _get_output_filename(self):
        """
        Return the filename for the generated (output) Excel file.

        Override this in child modules to provide a more descriptive or
        date-stamped filename.

        Returns:
            str: Output filename including ``.xlsx`` extension.

        Default behavior:
            ``'template_sale_report.xlsx'`` → ``'sale_report_output.xlsx'``

        Child Example::

            def _get_output_filename(self):
                date_str = fields.Date.today().strftime('%Y%m%d')
                return f'Sale_Report_{date_str}.xlsx'
        """
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
            2. Locate <TABLE_START> marker → (start_row, start_col).
            3. Retrieve dataset via _get_report_data().
            4. Determine performance mode (Normal vs Fast).
            5. Insert blank rows for the dataset.
            6. [Normal Mode] Copy styles from template row to inserted rows.
            7. Write data via _write_table_data().
            8. Replace placeholders via _get_header_footer_data().
            9. [Normal Mode] Auto-fit column widths.
            10. Export workbook → base64 → wizard download field.

        Returns:
            dict: ``ir.actions.act_window`` action reloading the wizard form
                  with ``state='download'`` to expose the file download widget.

        Raises:
            UserError: Template not found / unreadable, marker missing,
                       dataset empty, or any unhandled openpyxl exception.
        """
        self.ensure_one()

        # Step 1 ── Load template
        wb, sheet = self._load_template()

        # Step 2 ── Find table anchor
        start_row, start_col = self._find_table_marker(sheet)

        # Step 3 ── Get data
        data = self._get_report_data()
        total_records = len(data)

        if total_records == 0:
            raise UserError(
                'No records found for the selected criteria.\n'
                'Please adjust your filter parameters and try again.'
            )

        # Step 4 ── Performance mode
        is_fast_mode = total_records >= FAST_MODE_THRESHOLD

        # Step 5 ── Insert rows
        if total_records > 1:
            # Insert (total_records - 1) blank rows immediately below the marker row.
            # All rows below the marker (Footer, Grand Total, signatures…)
            # are automatically pushed down while preserving their own styles.
            sheet.insert_rows(start_row + 1, amount=total_records - 1)

            # Step 6 ── Copy styles (Normal Mode only)
            if not is_fast_mode:
                self._copy_row_styles(sheet, start_row, total_records)

        # Step 7 ── Write table data
        self._write_table_data(sheet, data, start_row, start_col)

        # Step 8 ── Replace Header / Footer placeholders
        end_row = start_row + total_records - 1
        hf_data = self._get_header_footer_data(start_row, end_row, start_col)
        if hf_data:
            self._replace_placeholders(sheet, hf_data)

        # Step 9 ── Auto-fit columns (Normal Mode only)
        if not is_fast_mode:
            self._autofit_columns(sheet, start_row, end_row)

        # Step 10 ── Export
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
            file_bytes   = base64.b64decode(attachment.datas)
            virtual_file = io.BytesIO(file_bytes)
            wb           = openpyxl.load_workbook(virtual_file)
            sheet        = wb.active
        except Exception as exc:
            raise UserError(
                f"Failed to read the Excel template '{template_name}'.\n"
                f"Ensure the file is a valid .xlsx workbook.\n\n"
                f"Technical detail: {exc}"
            ) from exc

        return wb, sheet

    def _find_table_marker(self, sheet):
        """
        Perform a full-sheet scan to locate the TABLE_START_MARKER cell.

        Iterates row by row, cell by cell. Stops and returns coordinates
        immediately upon the first match. The scan is short-circuited after
        finding the marker, so performance impact is minimal even for large
        template headers.

        Args:
            sheet (openpyxl.worksheet.worksheet.Worksheet): Worksheet to scan.

        Returns:
            tuple[int, int]: ``(row_index, column_index)`` — Both 1-based integers.
                             Example: Cell B10 → ``(10, 2)``.

        Raises:
            UserError: Marker string not found anywhere in the worksheet.
        """
        for row in sheet.iter_rows():
            for cell in row:
                if (
                    cell.value is not None
                    and str(cell.value).strip() == TABLE_START_MARKER
                ):
                    return cell.row, cell.column

        raise UserError(
            f"Marker '{TABLE_START_MARKER}' was not found in the template "
            f"'{self._get_template_name()}'.\n\n"
            "Please add this marker string to the leftmost cell of the first "
            "data row in the template and re-upload the file."
        )

    def _copy_row_styles(self, sheet, source_row, total_records):
        """
        Copy all visual formatting from the template row to newly inserted blank rows.

        Called in Normal Mode only (total_records < FAST_MODE_THRESHOLD).

        Copies the following style attributes for each column in the sheet:
            * ``font``          — Typeface, size, bold, italic, color, underline.
            * ``border``        — Left/right/top/bottom edge style and color.
            * ``fill``          — Background color (solid, gradient, pattern).
            * ``alignment``     — Horizontal/vertical alignment, wrap text, indent.
            * ``number_format`` — Display format string (date, currency, %, etc.).

        Each style object is deep-copied using ``copy()`` to ensure that changes
        to one cell's style object do not propagate to other cells sharing the
        same Python object reference (a common openpyxl pitfall).

        ``number_format`` is a plain string and does not require deep copy.

        Args:
            sheet         (openpyxl.worksheet.worksheet.Worksheet): Active worksheet.
            source_row    (int): 1-based index of the template/marker row.
            total_records (int): Total data rows (determines how many rows to style).

        Notes:
            * Only processes cells where ``has_style is True`` to skip
              genuinely blank cells and reduce iteration overhead.
            * Processes columns 1 through ``sheet.max_column``.
        """
        max_col = sheet.max_column

        for row_offset in range(1, total_records):
            target_row = source_row + row_offset

            for col_idx in range(1, max_col + 1):
                src = sheet.cell(row=source_row, column=col_idx)
                tgt = sheet.cell(row=target_row, column=col_idx)

                if not src.has_style:
                    continue

                tgt.font          = copy(src.font)
                tgt.border        = copy(src.border)
                tgt.fill          = copy(src.fill)
                tgt.alignment     = copy(src.alignment)
                tgt.number_format = src.number_format   # str — no copy needed

    def _replace_placeholders(self, sheet, placeholder_map):
        """
        Scan every cell in the worksheet and replace placeholder strings with values.

        Supports:
            * Partial replacement: ``'Ngày: {{DATE}}'`` → ``'Ngày: 31/07/2026'``
            * Multiple placeholders in one cell: replaces all matching keys.
            * Excel formula injection: if the replacement value starts with ``'='``,
              Excel will evaluate it as a formula when the file is opened.

        Called AFTER table rows are inserted and data is written, so:
            * Header rows remain at their original row indices.
            * Footer/Grand Total rows are already at their final pushed-down positions.

        Args:
            sheet           (openpyxl.worksheet.worksheet.Worksheet): Active worksheet.
            placeholder_map (dict[str, str]):
                            ``{ '{{PLACEHOLDER}}': 'replacement_value', ... }``

        Notes:
            * Non-string cell values (int, float, datetime, None) are skipped.
            * Replacement values are coerced to ``str`` before substitution.
        """
        for row in sheet.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str):
                    continue

                for placeholder, replacement in placeholder_map.items():
                    if placeholder in cell.value:
                        cell.value = cell.value.replace(
                            placeholder,
                            str(replacement),
                        )

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
            sheet     (openpyxl.worksheet.worksheet.Worksheet): Active worksheet.
            start_row (int): First data row (1-based).
            end_row   (int): Last data row (1-based).

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

            new_width = min(
                (max_length * COLUMN_WIDTH_FONT_FACTOR) + COLUMN_WIDTH_PADDING,
                MAX_COLUMN_WIDTH,
            )

            # Respect template's manually set column widths — only widen, never narrow
            current_width = sheet.column_dimensions[col_letter].width or 0
            if new_width > current_width:
                sheet.column_dimensions[col_letter].width = new_width

    def _export_file(self, wb):
        """
        Serialize the populated workbook to base64 and expose it for download.

        Saves the workbook into a fresh ``BytesIO`` buffer (separate from the
        input buffer, so the original template bytes are never overwritten).
        Encodes the buffer contents to base64 and writes to the ``excel_file``
        Binary field. Transitions the wizard state to ``'download'``.

        Args:
            wb (openpyxl.Workbook): Fully populated workbook ready for export.

        Returns:
            dict: ``ir.actions.act_window`` action to reload the current wizard
                  record in a new popup window, now showing the download widget.
        """
        output_buffer = io.BytesIO()
        wb.save(output_buffer)
        output_buffer.seek(0)

        self.write({
            'excel_file': base64.b64encode(output_buffer.read()),
            'file_name' : self._get_output_filename(),
            'state'     : 'download',
        })

        return {
            'type'      : 'ir.actions.act_window',
            'res_model' : self._name,
            'res_id'    : self.id,
            'view_mode' : 'form',
            'target'    : 'new',
        }
