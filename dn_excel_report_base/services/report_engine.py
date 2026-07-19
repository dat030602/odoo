# -*- coding: utf-8 -*-
from odoo import models, api
import xlsxwriter
import io
import base64


class ReportEngine(models.AbstractModel):
    _name = 'report.engine'
    _description = 'Dynamic Excel Report Abstract Engine'

    def generate_excel(self, report_code, data_records):
        """
        Main hook to generate the Excel file based on configuration.
        :param report_code: Code of the excel.report record
        :param data_records: List of dictionaries or recordset containing the prepared data
        :return: Base64 string of the generated file
        """
        report_config = self.env['excel.report'].search([('code', '=', report_code)], limit=1)
        if not report_config:
            raise ValueError(f"Report configuration with code '{report_code}' not found.")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(report_config.name)

        # 1. Setup layout & Page Setup
        self._prepare_worksheet(sheet, report_config)
        
        # 2. Compile Formats
        formats = self._prepare_formats(workbook, report_config)
        
        # 3. Render Flow
        current_row = 0
        current_row = self._render_header(sheet, formats, report_config, current_row)
        current_row = self._render_title(sheet, formats, report_config, current_row)
        current_row = self._render_table(sheet, formats, report_config, data_records, current_row)
        current_row = self._render_footer(sheet, formats, report_config, current_row)
        self._render_signature(sheet, formats, report_config, current_row)

        workbook.close()
        output.seek(0)
        return base64.b64encode(output.read())

    def _prepare_worksheet(self, sheet, report_config):
        """Setup worksheet layout, page orientation, paper size, margins, and column widths based on UI configuration"""
        sheet.set_landscape()
        sheet.set_paper(9)  # A4
        sheet.fit_to_pages(1, 0)
        sheet.center_horizontally()
        sheet.set_margins(left=0.3, right=0.3, top=0.5, bottom=0.5)

        # Set column widths based on the configuration, only for visible columns
        for i, col in enumerate(report_config.column_ids.filtered('is_visible')):
            sheet.set_column(i, i, col.width)

    def _prepare_formats(self, workbook, report_config):
        """Setup all formats from UI Configuration into Workbook"""
        formats = {}
        for fmt in report_config.format_ids:
            formats[fmt.id] = workbook.add_format(fmt.get_format_dict())
        
        # Provide default formats if missing
        if 'header' not in formats:
            formats['header'] = workbook.add_format({'bold': True, 'align': 'center', 'border': 1, 'valign': 'vcenter', 'text_wrap': True})
        if 'title' not in formats:
            formats['title'] = workbook.add_format({'bold': True, 'align': 'center', 'size': 14, 'valign': 'vcenter'})
        if 'default' not in formats:
            formats['default'] = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
            
        # Add specific signature formats from the old code
        formats.update({
            "signature_name": workbook.add_format({'bold': True, 'align': 'center', 'text_wrap': True, 'valign': 'vcenter', 'size': 12}),
            "signature_note": workbook.add_format({'italic': True, 'align': 'center', 'text_wrap': True, 'size': 12}),
            "signature_date": workbook.add_format({'italic': True, 'align': 'center', 'text_wrap': True, 'size': 11}),
        })
        return formats

    def _render_header(self, sheet, formats, report_config, start_row):
        """Can be overridden in child modules to draw company header information (Name, Tax ID, Address)"""
        return start_row

    def _render_title(self, sheet, formats, report_config, start_row):
        """Write the main and sub titles of the report"""
        visible_columns = report_config.column_ids.filtered('is_visible')
        cols_count = max(0, len(visible_columns) - 1)
        
        if report_config.report_title:
            title_fmt = formats.get('title')
            self._write_merged_cells(sheet, start_row, 0, start_row, cols_count, report_config.report_title, title_fmt, formats)
            start_row += 1
            
        if report_config.report_subtitle:
            sub_fmt = formats.get('signature_date')
            self._write_merged_cells(sheet, start_row, 0, start_row, cols_count, report_config.report_subtitle, sub_fmt, formats)
            start_row += 2
            
        return start_row

    def _render_table(self, sheet, formats, report_config, data_records, start_row):
        """Render the main data table with headers, body, and totals if applicable."""
        visible_columns = report_config.column_ids.filtered('is_visible')
        if not visible_columns:
            return start_row
        
        # 1. Vẽ dòng Header của Bảng
        for col_idx, col in enumerate(visible_columns):
            header_fmt = formats.get(col.format_id.id, formats['header'])
            sheet.write(start_row, col_idx, col.name, header_fmt)
        start_row += 1

        # 1. Initialize totals dictionary for columns that require summation
        totals = {col.field_name: 0 for col in visible_columns if col.is_sum}

        # 2. Render data rows
        for record in data_records:
            is_dict = isinstance(record, dict)
            
            for col_idx, col in enumerate(visible_columns):
                raw_value = record.get(col.field_name, '') if is_dict else getattr(record, col.field_name, '')
                
                if col.function_id:
                    raw_value = col.function_id.execute(raw_value)

                if col.is_sum and isinstance(raw_value, (int, float)):
                    totals[col.field_name] += raw_value

                cell_fmt = formats.get(col.format_id.id, formats['default'])
                self._write_cell(sheet, start_row, col_idx, raw_value, cell_fmt, formats)
            start_row += 1

        if totals:
            sheet.write(start_row, 0, "TỔNG CỘNG / TOTAL", formats['header'])
            # Điền trống các ô còn lại thuộc cột không tính tổng để giữ nguyên đường viền gridline
            for col_idx, col in enumerate(visible_columns):
                if col_idx == 0:
                    continue
                cell_fmt = formats.get(col.format_id.id, formats['header'])
                if col.is_sum:
                    sheet.write(start_row, col_idx, totals.get(col.field_name, 0), cell_fmt)
                else:
                    sheet.write(start_row, col_idx, "", cell_fmt)
            start_row += 1

        return start_row

    def _render_footer(self, sheet, formats, report_config, start_row):
        """Can be overridden in child modules to write footer notes or additional terms"""
        return start_row + 1

    def _render_signature(self, sheet, formats, report_config, start_row):
        """Render the signature section automatically aligned based on the number of signers (from the old _prepare_signature function)"""
        signatures = report_config.signature_ids
        if not signatures:
            return start_row
        
        # Ensure that the signature section starts at least 3 rows below the last data row to avoid overlap
        start_row = max(start_row, sheet.dim_rowmax + 3)
        
        visible_columns = report_config.column_ids.filtered('is_visible')
        total_cols = len(visible_columns)
        last_col_idx = max(0, total_cols - 1)
        
        # 1. Write the date row (Right-aligned, default merge 3 last columns)
        date_start_col = max(0, last_col_idx - 2)
        self._write_merged_cells(
            sheet, start_row, date_start_col, start_row, last_col_idx,
            "Date: " + report_config.signature_date if report_config.signature_date else "Date: ..............................",
            formats["signature_date"], formats,
        )
        start_row += 1
        
        # 2. Calculate the width of each signature block based on the number of signatures and total columns
        num_blocks = len(signatures)
        block_width = max(1, total_cols // num_blocks)
        
        # 2. Write Roles (Phase 1: Render Roles)
        current_col = 0
        for i, sig in enumerate(signatures):
            start_col = current_col
            end_col = last_col_idx if i == num_blocks - 1 else start_col + block_width - 1
            
            sig_data = sig.get_signature_data()
            self._write_merged_cells(sheet, start_row, start_col, start_row, end_col, sig_data['title'], formats["signature_name"], formats)
            current_col = end_col + 1
            
        # Leave some space for physical signature
        start_row += 5
        
        # 3. Write Signers' Names (Phase 2: Render Signers' Names)
        current_col = 0
        for i, sig in enumerate(signatures):
            start_col = current_col
            end_col = last_col_idx if i == num_blocks - 1 else start_col + block_width - 1
            
            sig_data = sig.get_signature_data()
            self._write_merged_cells(sheet, start_row, start_col, start_row, end_col, sig_data['value'], formats["signature_name"], formats)
            current_col = end_col + 1
            
        return start_row

    def _write_cell(self, sheet, row, col, cell_value, cell_format, formats):
        """Core function to analyze data types (base64 images, formula cells =, regular strings)"""
        if isinstance(cell_value, dict) and cell_value.get('type') == 'image':
            sheet.write(row, col, "", cell_format)
            b64_data = cell_value.get('data')
            if b64_data:
                try:
                    image_buffer = io.BytesIO(base64.b64decode(b64_data))
                    sheet.embed_image(row, col, 'image.png', {'image_data': image_buffer})
                except Exception:
                    sheet.write(row, col, "", cell_format)
        elif isinstance(cell_value, str) and cell_value.startswith('='):
            sheet.write_formula(row, col, cell_value, cell_format)
        else:
            sheet.write(row, col, cell_value, cell_format)

    def _write_merged_cells(self, sheet, r1, c1, r2, c2, cell_value, cell_format, formats):
        """Function to write merged cells with proper formatting and value handling"""
        sheet.merge_range(r1, c1, r2, c2, "", cell_format)
        self._write_cell(sheet, r1, c1, cell_value, cell_format, formats)