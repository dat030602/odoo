# Copyright 2024
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _


class ExcelColumnConfig(models.Model):
    _name = 'excel.column.config'
    _description = 'Excel Column Configuration'
    _order = 'sequence, id'

    name = fields.Char('Column Name', required=True, help="Internal column identifier")
    display_name = fields.Char('Display Name', required=True, translate=True,
                              help="Column header text in Excel")
    field_name = fields.Char('Field Name', required=True,
                            help="Field name in data provider result")
    
    # Relationships
    report_id = fields.Many2one('excel.report', string='Report', 
                               ondelete='cascade', required=True)
    template_id = fields.Many2one('excel.template', string='Template',
                                  ondelete='cascade')
    
    # Column properties
    sequence = fields.Integer('Sequence', default=10, required=True)
    column_width = fields.Float('Column Width', default=15.0,
                               help="Column width in characters")
    visible = fields.Boolean('Visible', default=True)
    
    # Alignment
    horizontal_align = fields.Selection([
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right'),
        ('fill', 'Fill'),
        ('justify', 'Justify'),
    ], string='Horizontal Alignment', default='left')
    
    vertical_align = fields.Selection([
        ('top', 'Top'),
        ('center', 'Center'),
        ('bottom', 'Bottom'),
    ], string='Vertical Alignment', default='center')
    
    # Formatting
    header_format_id = fields.Many2one('excel.cell.format', string='Header Format',
                                      help="Format for header cell")
    cell_format_id = fields.Many2one('excel.cell.format', string='Cell Format',
                                    help="Format for data cells")
    summary_format_id = fields.Many2one('excel.cell.format', string='Summary Format',
                                       help="Format for summary cell")
    
    # Number format override
    number_format = fields.Char('Number Format Override',
                                help="Override cell format number format")
    
    # Header merge configuration
    merge_with_column_id = fields.Many2one('excel.column.config', string='Merge With Column',
                                          help="Merge this header with another column")
    merge_header_text = fields.Char('Merge Header Text',
                                   help="Text to display when merged")
    
    # Summary configuration
    summary_type = fields.Selection([
        ('none', 'None'),
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('count', 'Count'),
    ], string='Summary Type', default='none')
    
    summary_label = fields.Char('Summary Label', help="Label for summary row")
    show_summary_label = fields.Boolean('Show Summary Label', default=True)
    
    # Data type hint
    data_type = fields.Selection([
        ('string', 'String'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
        ('boolean', 'Boolean'),
        ('currency', 'Currency'),
    ], string='Data Type', default='string', required=True,
       help="Hint for formatting and validation")
    
    @api.constrains('merge_with_column_id')
    def _check_merge_cycle(self):
        for column in self:
            if column.merge_with_column_id:
                # Check for cycles
                current = column.merge_with_column_id
                visited = [column.id]
                while current:
                    if current.id in visited:
                        raise models.ValidationError(_('Circular merge reference detected'))
                    visited.append(current.id)
                    current = current.merge_with_column_id
    
    def get_column_letter(self, index):
        """Convert column index to Excel column letter"""
        letters = ''
        while index >= 0:
            letters = chr(65 + (index % 26)) + letters
            index = index // 26 - 1
        return letters
    
    def get_data_type_format(self):
        """Get default number format based on data type"""
        self.ensure_one()
        formats = {
            'number': '#,##0.00',
            'date': 'dd/mm/yyyy',
            'datetime': 'dd/mm/yyyy hh:mm:ss',
            'currency': '#,##0.00 [$€-1]',
            'boolean': '@',
        }
        return formats.get(self.data_type, '@')
    
    @api.onchange('data_type')
    def _onchange_data_type(self):
        """Set default alignment based on data type"""
        if self.data_type in ['number', 'currency', 'date', 'datetime']:
            self.horizontal_align = 'right'
        elif self.data_type == 'boolean':
            self.horizontal_align = 'center'
        else:
            self.horizontal_align = 'left'
        
        # Set default number format
        if not self.number_format:
            self.number_format = self.get_data_type_format()