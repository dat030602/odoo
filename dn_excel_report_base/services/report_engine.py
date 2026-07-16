import base64
import io

from odoo import api, fields, models


class ReportEngine(models.AbstractModel):
    _name = "report.engine"
    _description = "Report Engine"
    _inherit = "report.abstract.report"

    @staticmethod
    def _init_sum(columns):
        """Initialize a dictionary to hold the sum of specified columns."""
        return {col['field']: 0 for col in columns if col.get('sum')}

    @staticmethod
    def _format_workbook(workbook, **kwargs):
        """Format the given workbook with specified formatting options."""
        format = workbook.add_format()

        for key, value in kwargs.items():
            method_name = f"set_{key}"
            if hasattr(format, method_name):
                getattr(format, method_name)(value)
            else:
                raise ValueError(f"Invalid keyword argument: {method_name}")

        return format

    def _prepare_formats(self, workbook, columns):
        """Prepare and return a dictionary of formats for the given columns."""
        res = {}
        for column in columns:
            if column.format_id:
                format = column.format_id
                res[format.name] = self._format_workbook(workbook, **format.get_format_dict())
        res.update({
            # Signature
            "signature_name": self._format_workbook(workbook, 12, bold=True, align="center", text_wrap=True, valign="vcenter"),
            "signature_note": self._format_workbook(workbook, 12, italic=True, align="center", text_wrap=True),
            "signature_date": self._format_workbook(workbook, 11, italic=True, align="center", text_wrap=True),
        })
        return res

    def _get_title(self, report):
        """Get the title for the given report."""
        return report.name if report.name else report._description

    def _get_report_data(self, object):
        """Get the data for the given object."""
        model = self.env[object.model_id.model]
        return model.search([])

    def _setup_worksheet_print(self, worksheet):
        """Set up the worksheet for printing.
        Example:
            worksheet.set_landscape()
            worksheet.set_paper(9)
            worksheet.fit_to_pages(1, 0)
            worksheet.center_horizontally()
            worksheet.set_margins(left=0.3, right=0.3, top=0.5, bottom=0.5)
        """
        pass

    def _get_columns(self, report):
        """Get the columns for the given report, sorted by sequence."""
        return report.column_ids.sorted(key=lambda c: c.sequence)

    def _prepare_header(self, report_id, worksheet, formats, current_row):
        """Prepare the header for the report."""
        title = self._get_title(report_id)
        self.write_merged_cells(
            worksheet,
            current_row,
            0,
            current_row,
            len(self._get_columns(report_id)) - 1,
            title,
            formats.get("header", self._format_workbook(worksheet, 14, bold=True, align="center", text_wrap=True)),
        )
        current_row += 1
        return current_row

    def _prepare_body(self, report_id, worksheet, formats, current_row):
        """Prepare the body for the report."""
        # Implement body preparation logic here
        return current_row

    def _prepare_header_table(self, report_id, worksheet, formats, columns, current_row, records):
        """Prepare the header table for the report."""
        row_group = 5 if obj.month and obj.year else 5
        row_detail = 6 if obj.month and obj.year else 6

        # Điều chỉnh nếu có dòng tháng/năm
        if obj.month and obj.year:
            row_group = 6
            row_detail = 7

        col = 0
        last_group = None
        group_start_col = 0

        i = 0
        for column in columns:
            group = column.merge_row

            if not column.merge_row:
                worksheet.merge_range(row_group, col, row_detail, col, column.name, formats["header"])
            else:
                worksheet.merge_range(row_group, col, row_detail, col, column.name, formats["header"])
            i += 1
            col += 1

        return current_row

    def _prepare_table(self, report_id, worksheet, formats, current_row, records):
        """Prepare the table for the report."""
        # Implement table preparation logic here
        return current_row

    def _prepare_footer(self, report_id, worksheet, formats, current_row):
        """Prepare the footer for the report."""
        # Implement footer preparation logic here
        return current_row

    def _get_signature_blocks(self, report_id):
        """Get the signature blocks for the report."""
        signers = report_id.signer_ids
        signature_blocks = []
        for signer in signers:
            signature_blocks.append({
                "role": signer.name,
                "signer": signer.user_id.name or signer.fixed_name,
            })
        return signature_blocks

    def _get_signature_blocks(self, report):
        """Get the signature blocks for the report."""
        signers = report.signer_ids
        blocks = []
        for signer in signers:
            blocks.append({
                "role": signer.name,
                "signer": signer.user_id.name or signer.fixed_name,
            })
        return blocks

    def _prepare_signature(self, report_id, worksheet, formats, columns, current_row):
        """Prepare the signature section for the report."""
        # Position the signature section 3 rows below the maximum filled row
        current_row = worksheet.dim_rowmax + 3

        last_col_idx = len(columns) - 1
        total_cols = len(columns)

        # Calculate merge columns for the date line (aligning to the right)
        date_start_col = max(0, last_col_idx - 2)
        date_end_col = last_col_idx

        # Write the international date placeholder using helper method
        self.write_merged_cells(
            worksheet,
            current_row,
            date_start_col,
            current_row,
            date_end_col,
            "Date: .........................",
            formats["signature_date"]
        )

        current_row += 1

        # Retrieve signature blocks
        sig_blocks = self._get_signature_blocks(report)
        num_blocks = len(sig_blocks)

        # Calculate the column width allocation for each signature block
        col_width = max(1, total_cols // num_blocks)

        # Phase 1: Render the Roles (e.g., Creator, Approver)
        col_idx = 0
        for i, block in enumerate(sig_blocks):
            start_col = col_idx
            end_col = last_col_idx if i == num_blocks - 1 else start_col + col_width - 1

            self.write_merged_cells(
                worksheet,
                current_row,
                start_col,
                current_row,
                end_col,
                block["role"],
                formats["signature_name"]
            )

            col_idx = end_col + 1

        # Leave a vertical gap of 4 rows for physical signatures
        current_row += 5

        # Phase 2: Render the Signers' Names
        col_idx = 0
        for i, block in enumerate(sig_blocks):
            start_col = col_idx
            end_col = last_col_idx if i == num_blocks - 1 else start_col + col_width - 1

            self.write_merged_cells(
                worksheet,
                current_row,
                start_col,
                current_row,
                end_col,
                block["signer"],
                formats["signature_name"],
            )

            col_idx = end_col + 1

        return current_row

    def write_cell(self, worksheet, row, col, cell_value, cell_format):
        if isinstance(cell_value, dict) and cell_value.get('type') == 'image':
            worksheet.write(row, col, "", cell_format)
            b64_data = cell_value.get('data')
            if b64_data:
                try:
                    image_buffer = io.BytesIO(base64.b64decode(b64_data))
                    # worksheet.insert_image(row, col, 'image.png', {
                    #     'image_data': image_buffer
                    # })
                    worksheet.embed_image(row, col, 'image.png', {
                        'image_data': image_buffer
                    })
                except Exception as e:
                    worksheet.write(row, col, "", cell_format)

        elif isinstance(cell_value, str) and cell_value.startswith('='):
            worksheet.write_formula(row, col, cell_value, cell_format)
        else:
            worksheet.write(row, col, cell_value, cell_format)

    def write_merged_cells(self, worksheet, r1, c1, r2, c2, cell_value, cell_format):
        worksheet.merge_range(r1, c1, r2, c2, "", cell_format)
        self.write_cell(worksheet, r1, c1, cell_value, cell_format)

    @api.model
    def generate(self, workbook, worksheet):
        report_id = self.env['excel.report'].search([('technical_name', '=', self._name)], limit=1)
        self._setup_worksheet_print(worksheet)
        self._setup_column_widths(worksheet)
        current_row = 0

        columns = self._get_columns(report_id)
        formats = self._prepare_formats(workbook, columns)

        data_records = self._get_report_data(report_id)

        current_row = self._prepare_header(report_id, worksheet, formats, current_row)
        current_row = self._prepare_body(report_id, worksheet, formats, current_row)
        current_row = self._prepare_header_table(report_id, worksheet, formats, columns, current_row, data_records)
        current_row = self._prepare_table(report_id, worksheet, formats, current_row, data_records)
        current_row = self._prepare_footer(report_id, worksheet, formats, current_row)
        current_row = self._prepare_signature(report_id, worksheet, formats, columns, current_row)
