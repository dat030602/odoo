# Copyright 2024
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, api, _


class ExcelReportAbstract(models.AbstractModel):
    _name = 'excel.report.abstract'
    _description = 'Abstract Excel Report Provider'
    _inherit = 'report.report_xlsx.abstract'

    @api.model
    def get_report_data(self, records, context=None):
        """
        Return report data as list of dictionaries.
        This method should be overridden by specific report providers.
        
        Args:
            records: Odoo recordset to report on
            context: Optional context dictionary
            
        Returns:
            List of dictionaries with report data
        """
        return []

    def generate_xlsx_report(self, workbook, data, objects):
        """
        Generate XLSX report using the dynamic framework.
        
        Args:
            workbook: XlsxWriter workbook object
            data: Report data dictionary
            objects: Odoo recordset
        """
        # Get report configuration from data
        report_config_id = data.get('report_config_id')
        if not report_config_id:
            raise ValueError(_('Report configuration ID not provided'))
        
        report_config = self.env['excel.report'].browse(report_config_id)
        if not report_config.exists():
            raise ValueError(_('Report configuration not found'))
        
        # Get report data from provider
        report_data = report_config.get_report_data(objects)
        
        # Render report sections
        self._render_report(workbook, report_config, report_data, objects)
    
    def _render_report(self, workbook, report_config, report_data, objects):
        """
        Render complete report with all sections.
        
        Args:
            workbook: XlsxWriter workbook object
            report_config: Excel report configuration
            report_data: Data from provider
            objects: Original Odoo recordset
        """
        # Create worksheet
        sheet_name = report_config.sheet_name or 'Report'
        sheet = workbook.add_worksheet(sheet_name[:31])  # Excel sheet name limit
        
        # Render sections
        current_row = 0
        
        # Header
        if report_config.header_layout_id:
            current_row = self._render_header(
                sheet, workbook, report_config, report_data, objects, current_row
            )
        
        # Body layouts
        for layout in report_config.body_layout_ids.sorted('sequence'):
            current_row = self._render_body_layout(
                sheet, workbook, layout, report_config, report_data, objects, current_row
            )
        
        # Main table
        if report_config.column_ids and report_data:
            current_row = self._render_table(
                sheet, workbook, report_config, report_data, current_row
            )
        
        # Footer
        if report_config.footer_layout_id:
            self._render_footer(
                sheet, workbook, report_config.footer_layout_id, 
                report_config, report_data, objects, current_row
            )
        
        # Apply global settings
        self._apply_global_settings(sheet, workbook, report_config)
    
    def _render_header(self, sheet, workbook, report_config, report_data, objects, start_row):
        """
        Render header section.
        
        Args:
            sheet: XlsxWriter worksheet object
            workbook: XlsxWriter workbook object
            report_config: Report configuration
            report_data: Report data
            objects: Original recordset
            start_row: Starting row index
            
        Returns:
            Next available row index
        """
        layout = report_config.header_layout_id
        if not layout:
            return start_row
        
        # Render layout cells
        for cell in layout.cell_ids.sorted('row'):
            self._render_layout_cell(
                sheet, workbook, cell, report_data, report_config, objects, start_row
            )
        
        # Set row heights
        for row in range(layout.row_count):
            sheet.set_row(start_row + row, report_config.header_row_height)
        
        return start_row + layout.row_count
    
    def _render_body_layout(self, sheet, workbook, layout, report_config, 
                           report_data, objects, start_row):
        """
        Render body layout section.
        
        Args:
            sheet: XlsxWriter worksheet object
            workbook: XlsxWriter workbook object
            layout: Layout configuration
            report_config: Report configuration
            report_data: Report data
            objects: Original recordset
            start_row: Starting row index
            
        Returns:
            Next available row index
        """
        # Render layout cells
        for cell in layout.cell_ids.sorted('row'):
            self._render_layout_cell(
                sheet, workbook, cell, report_data, report_config, objects, start_row
            )
        
        # Set row heights
        for row in range(layout.row_count):
            sheet.set_row(start_row + row, report_config.data_row_height)
        
        return start_row + layout.row_count
    
    def _render_table(self, sheet, workbook, report_config, report_data, start_row):
        """
        Render main data table.
        
        Args:
            sheet: XlsxWriter worksheet object
            workbook: XlsxWriter workbook object
            report_config: Report configuration
            report_data: Report data
            start_row: Starting row index
            
        Returns:
            Next available row index
        """
        columns = report_config.column_ids.sorted('sequence')
        
        # Render header row
        for col_idx, column in enumerate(columns):
            header_format = self._get_column_format(
                workbook, column.header_format_id, column
            )
            sheet.write(start_row, col_idx, column.display_name, header_format)
        
        sheet.set_row(start_row, report_config.header_row_height)
        
        # Render data rows
        for row_idx, row_data in enumerate(report_data):
            for col_idx, column in enumerate(columns):
                value = row_data.get(column.field_name, '')
                cell_format = self._get_column_format(
                    workbook, column.cell_format_id, column
                )
                sheet.write(start_row + row_idx + 1, col_idx, value, cell_format)
            
            sheet.set_row(start_row + row_idx + 1, report_config.data_row_height)
        
        # Render summary rows
        summary_rows = self._render_summary_rows(
            sheet, workbook, columns, report_data, start_row + len(report_data) + 1
        )
        
        # Apply column widths
        for col_idx, column in enumerate(columns):
            if column.column_width:
                sheet.set_column(col_idx, col_idx, column.column_width)
        
        # Apply auto-filter
        if report_config.auto_filter:
            sheet.autofilter(
                start_row, 0, 
                start_row + len(report_data), 
                len(columns) - 1
            )
        
        return start_row + len(report_data) + 1 + summary_rows
    
    def _render_summary_rows(self, sheet, workbook, columns, report_data, start_row):
        """
        Render summary rows for columns with summary configured.
        
        Args:
            sheet: XlsxWriter worksheet object
            workbook: XlsxWriter workbook object
            columns: Column configurations
            report_data: Report data
            start_row: Starting row index
            
        Returns:
            Number of summary rows added
        """
        summary_columns = columns.filtered(lambda c: c.summary_type != 'none')
        if not summary_columns:
            return 0
        
        # Label row
        for col_idx, column in enumerate(columns):
            if column.summary_type != 'none' and column.show_summary_label:
                label = column.summary_label or column.summary_type.capitalize()
                label_format = self._get_column_format(
                    workbook, column.summary_format_id, column
                )
                sheet.write(start_row, col_idx, label, label_format)
        
        # Value row
        for col_idx, column in enumerate(columns):
            if column.summary_type != 'none':
                values = [
                    row.get(column.field_name, 0) 
                    for row in report_data 
                    if isinstance(row.get(column.field_name), (int, float))
                ]
                
                if values:
                    summary_value = self._calculate_summary(values, column.summary_type)
                    value_format = self._get_column_format(
                        workbook, column.summary_format_id, column
                    )
                    sheet.write(start_row + 1, col_idx, summary_value, value_format)
        
        sheet.set_row(start_row, report_config.header_row_height)
        sheet.set_row(start_row + 1, report_config.data_row_height)
        
        return 2
    
    def _render_footer(self, sheet, workbook, layout, report_config, 
                      report_data, objects, start_row):
        """
        Render footer section.
        
        Args:
            sheet: XlsxWriter worksheet object
            workbook: XlsxWriter workbook object
            layout: Footer layout configuration
            report_config: Report configuration
            report_data: Report data
            objects: Original recordset
            start_row: Starting row index
        """
        # Render layout cells
        for cell in layout.cell_ids.sorted('row'):
            self._render_layout_cell(
                sheet, workbook, cell, report_data, report_config, objects, start_row
            )
        
        # Set row heights
        for row in range(layout.row_count):
            sheet.set_row(start_row + row, report_config.data_row_height)
    
    def _render_layout_cell(self, sheet, workbook, cell, report_data, 
                           report_config, objects, start_row):
        """
        Render a single layout cell.
        
        Args:
            sheet: XlsxWriter worksheet object
            workbook: XlsxWriter workbook object
            cell: Layout cell configuration
            report_data: Report data
            report_config: Report configuration
            objects: Original recordset
            start_row: Starting row index
        """
        # Get cell content
        content = self._get_cell_content(cell, report_data, report_config, objects)
        
        # Get cell format
        cell_format = None
        if cell.format_id:
            cell_format = cell.format_id.get_xlsx_format(workbook)
        
        # Calculate actual position
        actual_row = start_row + cell.row
        actual_col = cell.col
        
        # Apply merge if needed
        if cell.merge_rows > 1 or cell.merge_cols > 1:
            sheet.merge_range(
                actual_row, actual_col,
                actual_row + cell.merge_rows - 1,
                actual_col + cell.merge_cols - 1,
                content, cell_format
            )
        else:
            sheet.write(actual_row, actual_col, content, cell_format)
        
        # Apply row height override
        if cell.row_height:
            sheet.set_row(actual_row, cell.row_height)
    
    def _get_cell_content(self, cell, report_data, report_config, objects):
        """
        Get content for a layout cell.
        
        Args:
            cell: Layout cell configuration
            report_data: Report data
            report_config: Report configuration
            objects: Original recordset
            
        Returns:
            Cell content as string
        """
        if cell.content_type == 'static':
            return cell.static_text or ''
        
        elif cell.content_type == 'variable':
            return self._get_variable_value(cell.variable_name, report_data, report_config, objects)
        
        elif cell.content_type == 'expression':
            return self._evaluate_expression(cell.expression, report_data, report_config, objects)
        
        elif cell.content_type == 'empty':
            return ''
        
        return ''
    
    def _get_variable_value(self, variable_name, report_data, report_config, objects):
        """
        Get value of a variable.
        
        Args:
            variable_name: Name of the variable
            report_data: Report data
            report_config: Report configuration
            objects: Original recordset
            
        Returns:
            Variable value
        """
        # Common variables
        variables = {
            'company_name': self.env.company.name,
            'report_name': report_config.name,
            'current_date': self.env.context.get('current_date', 
                                                 fields.Date.context_today(self).strftime('%d/%m/%Y')),
            'current_time': fields.Datetime.now().strftime('%H:%M:%S'),
            'user_name': self.env.user.name,
            'timestamp': fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'record_count': len(objects),
        }
        
        return variables.get(variable_name, '')
    
    def _evaluate_expression(self, expression, report_data, report_config, objects):
        """
        Evaluate Python expression for dynamic content.
        
        Args:
            expression: Python expression string
            report_data: Report data
            report_config: Report configuration
            objects: Original recordset
            
        Returns:
            Evaluated result as string
        """
        if not expression:
            return ''
        
        # Prepare evaluation context
        context = {
            'data': report_data,
            'report': report_config,
            'objects': objects,
            'company': self.env.company,
            'user': self.env.user,
            'date': fields.Date.context_today(self),
            'datetime': fields.Datetime.now(),
            'len': len,
            'sum': sum,
            'avg': lambda x: sum(x) / len(x) if x else 0,
            'min': min,
            'max': max,
        }
        
        try:
            result = eval(expression, {'__builtins__': {}}, context)
            return str(result) if result is not None else ''
        except Exception as e:
            return '#ERROR: %s' % str(e)
    
    def _get_column_format(self, workbook, format_id, column):
        """
        Get format for a column cell.
        
        Args:
            workbook: XlsxWriter workbook object
            format_id: Cell format ID
            column: Column configuration
            
        Returns:
            XlsxWriter format object
        """
        if format_id:
            cell_format = format_id.get_xlsx_format(workbook)
        else:
            cell_format = workbook.add_format()
        
        # Apply number format override if specified
        if column.number_format:
            cell_format.set_num_format(column.number_format)
        elif column.data_type and column.data_type != 'string':
            # Apply default number format based on data type
            num_format = column.get_data_type_format()
            if num_format:
                cell_format.set_num_format(num_format)
        
        # Apply alignment
        if column.horizontal_align:
            cell_format.set_align(column.horizontal_align)
        if column.vertical_align:
            cell_format.set_valign(column.vertical_align)
        
        return cell_format
    
    def _calculate_summary(self, values, summary_type):
        """
        Calculate summary value based on type.
        
        Args:
            values: List of numeric values
            summary_type: Type of summary (sum, avg, min, max, count)
            
        Returns:
            Calculated summary value
        """
        if not values:
            return 0
        
        if summary_type == 'sum':
            return sum(values)
        elif summary_type == 'avg':
            return sum(values) / len(values)
        elif summary_type == 'min':
            return min(values)
        elif summary_type == 'max':
            return max(values)
        elif summary_type == 'count':
            return len(values)
        return 0
    
    def _apply_global_settings(self, sheet, workbook, report_config):
        """
        Apply global settings to the worksheet.
        
        Args:
            sheet: XlsxWriter worksheet object
            workbook: XlsxWriter workbook object
            report_config: Report configuration
        """
        # Freeze panes after header if configured
        if report_config.freeze_panes and report_config.header_layout_id:
            freeze_row = report_config.header_layout_id.row_count
            if freeze_row > 0:
                sheet.freeze_panes(freeze_row, 0)