# Copyright 2024
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _


class ExcelReport(models.Model):
    _name = 'excel.report'
    _description = 'Excel Report Configuration'
    _order = 'name, id'

    name = fields.Char('Report Name', required=True, translate=True)
    code = fields.Char('Report Code', required=True, help="Technical identifier for the report")
    description = fields.Text('Description', help="Report description for users")
    
    # Model and data provider
    model_id = fields.Many2one('ir.model', string='Model', required=True, 
                               help="Target model for this report")
    model_name = fields.Char(related='model_id.model', string='Model Name', store=True)
    provider = fields.Char('Data Provider', required=True,
                          help="Python class that provides report data")
    
    # Template and configuration
    template_id = fields.Many2one('excel.template', string='Report Template',
                                   help="Default template for this report")
    sheet_name = fields.Char('Sheet Name', default='Report', 
                             help="Name of the Excel sheet")
    
    # File configuration
    report_file_pattern = fields.Char('File Name Pattern', default='report_{date}',
                                      help="Pattern for generated file name. Use variables like {date}, {company}, etc.")
    
    # Layout sections
    header_layout_id = fields.Many2one('excel.layout', string='Header Layout',
                                       help="Header configuration for the report")
    body_layout_ids = fields.One2many('excel.layout', 'report_id', 
                                      string='Body Layouts',
                                      domain=[('layout_type', '=', 'body')],
                                      help="Additional body sections before the main table")
    footer_layout_id = fields.Many2one('excel.layout', string='Footer Layout',
                                       help="Footer configuration for the report")
    
    # Table configuration
    column_ids = fields.One2many('excel.column.config', 'report_id',
                                 string='Column Configuration',
                                 help="Table column definitions")
    
    # Configuration options
    auto_filter = fields.Boolean('Auto Filter', default=True,
                                  help="Add auto-filter to table headers")
    freeze_panes = fields.Boolean('Freeze Panes', default=True,
                                  help="Freeze header row when scrolling")
    header_row_height = fields.Integer('Header Row Height', default=25)
    data_row_height = fields.Integer('Data Row Height', default=20)
    
    # State and publishing
    active = fields.Boolean('Active', default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('published', 'Published'),
    ], string='Status', default='draft', required=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    
    @api.constrains('code')
    def _check_code_unique(self):
        for report in self:
            if self.search_count([('code', '=', report.code), ('id', '!=', report.id)]):
                raise models.ValidationError(_('Report code must be unique!'))
    
    def action_preview(self):
        """Preview the report with sample data"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Preview Report'),
            'res_model': 'excel.report.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_report_id': self.id}
        }
    
    def action_export(self):
        """Export the report for selected records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export Report'),
            'res_model': 'excel.report.export',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_report_id': self.id}
        }
    
    def get_report_data(self, records=None):
        """Get report data from the provider"""
        self.ensure_one()
        if not self.provider:
            return []
        
        try:
            provider_model = self.env[self.provider]
            if records is None:
                # Get all records from the model
                records = self.env[self.model_name].search([])
            return provider_model.get_report_data(records)
        except Exception as e:
            raise models.ValidationError(_('Error getting report data: %s') % str(e))
    
    def generate_excel(self, records=None):
        """Generate Excel file"""
        self.ensure_one()
        data = self.get_report_data(records)
        
        # Import xlsxwriter
        import xlsxwriter
        from io import BytesIO
        
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        try:
            # Render report sections
            self._render_header(workbook, data)
            self._render_body_layouts(workbook, data)
            self._render_table(workbook, data)
            self._render_footer(workbook, data)
            
            workbook.close()
            output.seek(0)
            return output.read()
        except Exception as e:
            workbook.close()
            raise models.ValidationError(_('Error generating Excel: %s') % str(e))
    
    def _render_header(self, workbook, data):
        """Render header section"""
        if not self.header_layout_id:
            return
        
        sheet = workbook.get_worksheet_by_name(self.sheet_name)
        if not sheet:
            sheet = workbook.add_worksheet(self.sheet_name)
        
        self.header_layout_id.render(sheet, workbook, data, self)
    
    def _render_body_layouts(self, workbook, data):
        """Render body layout sections"""
        sheet = workbook.get_worksheet_by_name(self.sheet_name)
        if not sheet:
            sheet = workbook.add_worksheet(self.sheet_name)
        
        current_row = 0
        if self.header_layout_id:
            current_row = self.header_layout_id.get_row_count()
        
        for layout in self.body_layout_ids:
            layout.render(sheet, workbook, data, self, start_row=current_row)
            current_row += layout.get_row_count()
    
    def _render_table(self, workbook, data):
        """Render main data table"""
        if not self.column_ids or not data:
            return
        
        sheet = workbook.get_worksheet_by_name(self.sheet_name)
        if not sheet:
            sheet = workbook.add_worksheet(self.sheet_name)
        
        # Calculate starting row
        start_row = 0
        if self.header_layout_id:
            start_row = self.header_layout_id.get_row_count()
        start_row += sum(layout.get_row_count() for layout in self.body_layout_ids)
        
        # Render table headers
        self._render_table_headers(sheet, workbook, start_row)
        
        # Render data rows
        self._render_data_rows(sheet, workbook, data, start_row + 1)
        
        # Render summary rows if configured
        summary_rows = self._render_summary_rows(sheet, workbook, data, start_row + len(data) + 1)
        
        # Calculate footer start row
        footer_start_row = start_row + len(data) + 1 + summary_rows
        
        # Render footer
        if self.footer_layout_id:
            self.footer_layout_id.render(sheet, workbook, data, self, start_row=footer_start_row)
        
        # Apply column widths
        self._apply_column_widths(sheet)
        
        # Apply auto-filter
        if self.auto_filter:
            sheet.autofilter(start_row, 0, start_row + len(data), len(self.column_ids) - 1)
        
        # Freeze panes
        if self.freeze_panes:
            sheet.freeze_panes(start_row + 1, 0)
    
    def _render_table_headers(self, sheet, workbook, start_row):
        """Render table header row"""
        for col_idx, column in enumerate(self.column_ids.sorted('sequence')):
            cell_format = column.header_format_id.get_xlsx_format(workbook) if column.header_format_id else None
            sheet.write(start_row, col_idx, column.display_name, cell_format)
            
            # Set row height
            sheet.set_row(start_row, self.header_row_height)
    
    def _render_data_rows(self, sheet, workbook, data, start_row):
        """Render data rows"""
        for row_idx, row_data in enumerate(data):
            for col_idx, column in enumerate(self.column_ids.sorted('sequence')):
                field_name = column.field_name
                value = row_data.get(field_name, '')
                
                cell_format = column.cell_format_id.get_xlsx_format(workbook) if column.cell_format_id else None
                
                # Apply number format if specified
                if column.number_format:
                    if not cell_format:
                        cell_format = workbook.add_format()
                    cell_format.set_num_format(column.number_format)
                
                sheet.write(start_row + row_idx, col_idx, value, cell_format)
                
                # Set row height
                sheet.set_row(start_row + row_idx, self.data_row_height)
    
    def _render_summary_rows(self, sheet, workbook, data, start_row):
        """Render summary rows for columns that have summary configured"""
        summary_columns = self.column_ids.filtered(lambda c: c.summary_type != 'none')
        if not summary_columns:
            return 0
        
        for col_idx, column in enumerate(self.column_ids.sorted('sequence')):
            if column.summary_type != 'none':
                values = [row.get(column.field_name, 0) for row in data if isinstance(row.get(column.field_name), (int, float))]
                
                if values:
                    summary_value = self._calculate_summary(values, column.summary_type)
                    
                    cell_format = column.summary_format_id.get_xlsx_format(workbook) if column.summary_format_id else None
                    label = column.summary_label or column.summary_type.capitalize()
                    
                    if column.show_summary_label:
                        sheet.write(start_row, col_idx, label, cell_format)
                    sheet.write(start_row + 1, col_idx, summary_value, cell_format)
        
        return 2
    
    def _calculate_summary(self, values, summary_type):
        """Calculate summary value based on type"""
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
    
    def _apply_column_widths(self, sheet):
        """Apply column widths"""
        for col_idx, column in enumerate(self.column_ids.sorted('sequence')):
            if column.column_width:
                sheet.set_column(col_idx, col_idx, column.column_width)