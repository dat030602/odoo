# -*- coding: utf-8 -*-
"""
wizard_sale_excel_report.py
============================

Sale Order Excel Report — inherits base.excel.report.

Template design (template_sale_report.xlsx):
    Row 1  : Company logo + {{COMPANY_NAME}}
    Row 2  : Report title
    Row 3  : Print date: {{PRINT_DATE}}
    Row 4  : (blank separator)
    Row 5  : Table column headers  [No., Order, Date, Customer, Subtaxed, Tax, Total]
    Row 6  : <TABLE_START>         ← data starts here
    Row 7  : {{GRAND_TOTAL_ROW}}   ← pushed down after insert_rows
    Row 8  : Signature area
"""

from odoo              import models, fields
from openpyxl.styles   import Font
from openpyxl.utils    import get_column_letter


class SaleExcelReport(models.TransientModel):

    _name        = 'sale.excel.report'
    _inherit     = 'base.excel.report'
    _description = 'Sale Order Excel Report'

    # ── Filter fields specific to this report ────────────────────────────────
    date_from = fields.Date(string='From Date')
    date_to   = fields.Date(string='To Date')

    # ── Column offset constants (relative to start_col returned by marker scan)
    # Keeps _write_table_data readable and easy to reorder later.
    _COL_NO      = 0   # Sequential number
    _COL_ORDER   = 1   # Sale order name
    _COL_DATE    = 2   # Order date
    _COL_PARTNER = 3   # Customer name
    _COL_UNTAXED = 4   # Untaxed amount
    _COL_TAX     = 5   # Tax amount
    _COL_TOTAL   = 6   # Total amount  ← used in SUBTOTAL formula

    # ── Number format strings ─────────────────────────────────────────────────
    _FMT_DATE   = 'DD/MM/YYYY'
    _FMT_NUMBER = '#,##0.00'

    # ─────────────────────────────────────────────────────────────────────────
    # HOOK IMPLEMENTATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def _get_template_name(self):
        return 'template_sale_report.xlsx'

    def _get_output_filename(self):
        date_str = fields.Date.today().strftime('%Y%m%d')
        return f'Sale_Report_{date_str}.xlsx'

    def _get_report_data(self):
        """
        Build flat list interleaved with per-partner subtotal markers.

        Dataset is sorted by partner then date so that grouping is contiguous.
        Each subtotal row counts as one physical Excel row in the output.
        """
        domain = [('state', 'in', ['sale', 'done'])]
        if self.date_from:
            domain.append(('date_order', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_order', '<=', self.date_to))

        records = self.env['sale.order'].search(
            domain, order='partner_id asc, date_order asc'
        )

        lines           = []
        current_partner = None

        for rec in records:
            # Emit subtotal when partner changes (skip on first record)
            if current_partner and current_partner != rec.partner_id:
                lines.append({
                    'row_type' : 'subtotal',
                    'label'    : f'Subtotal — {current_partner.name}',
                })

            lines.append({'row_type': 'data', 'record': rec})
            current_partner = rec.partner_id

        # Final group subtotal
        if current_partner:
            lines.append({
                'row_type' : 'subtotal',
                'label'    : f'Subtotal — {current_partner.name}',
            })

        return lines

    def _write_table_data(self, sheet, data, start_row, start_col):
        """
        Map each data/subtotal row to its Excel columns.

        Uses SUBTOTAL(9, range) for group totals so that the Grand Total
        placeholder (which also uses SUBTOTAL) does not double-count.
        """
        bold        = Font(bold=True)
        total_col_l = get_column_letter(start_col + self._COL_TOTAL)

        current_row     = start_row
        group_start_row = start_row
        seq_no          = 1

        for line in data:

            if line['row_type'] == 'data':
                rec = line['record']

                sheet.cell(row=current_row, column=start_col + self._COL_NO     ).value = seq_no

                sheet.cell(row=current_row, column=start_col + self._COL_ORDER  ).value = rec.name

                date_cell = sheet.cell(row=current_row, column=start_col + self._COL_DATE)
                date_cell.value         = rec.date_order.date() if rec.date_order else ''
                date_cell.number_format = self._FMT_DATE

                sheet.cell(row=current_row, column=start_col + self._COL_PARTNER).value = rec.partner_id.name

                for col_offset, amount in (
                    (self._COL_UNTAXED, rec.amount_untaxed),
                    (self._COL_TAX,     rec.amount_tax),
                    (self._COL_TOTAL,   rec.amount_total),
                ):
                    amt_cell = sheet.cell(row=current_row, column=start_col + col_offset)
                    amt_cell.value         = amount
                    amt_cell.number_format = self._FMT_NUMBER

                seq_no += 1

            elif line['row_type'] == 'subtotal':
                label_cell = sheet.cell(row=current_row, column=start_col + self._COL_PARTNER)
                label_cell.value = line['label']
                label_cell.font  = bold

                # SUBTOTAL(9, ...) is ignored by outer SUBTOTAL — avoids double count
                formula = (
                    f'=SUBTOTAL(9,'
                    f'{total_col_l}{group_start_row}:{total_col_l}{current_row - 1})'
                )
                sub_cell = sheet.cell(row=current_row, column=start_col + self._COL_TOTAL)
                sub_cell.value         = formula
                sub_cell.font          = bold
                sub_cell.number_format = self._FMT_NUMBER

                group_start_row = current_row + 1   # Next group starts on the next row

            current_row += 1

    def _get_header_footer_data(self, start_row, end_row, start_col):
        total_col_l = get_column_letter(start_col + self._COL_TOTAL)
        return {
            '{{COMPANY_NAME}}' : self.env.company.name,
            '{{PRINT_DATE}}'   : fields.Date.today().strftime('%d/%m/%Y'),
            '{{CREATOR}}'      : self.env.user.name,
            # Grand Total uses SUBTOTAL to skip embedded subtotal rows
            '{{GRAND_TOTAL}}'  : f'=SUBTOTAL(9,{total_col_l}{start_row}:{total_col_l}{end_row})',
        }
