# Copyright 2024
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _


class ExcelLayout(models.Model):
    _name = 'excel.layout'
    _description = 'Excel Layout Configuration'
    _order = 'layout_type, name, id'

    name = fields.Char('Layout Name', required=True, translate=True)
    code = fields.Char('Layout Code', required=True, help="Technical identifier for the layout")
    description = fields.Text('Description', help="Layout description for users")
    
    # Layout type
    layout_type = fields.Selection([
        ('header', 'Header'),
        ('body', 'Body'),
        ('footer', 'Footer'),
    ], string='Layout Type', required=True, default='body')
    
    # Relationships
    report_id = fields.Many2one('excel.report', string='Report',
                               ondelete='cascade', 
                               domain="[('layout_type', '=', 'body')]")
    
    # Layout cells
    cell_ids = fields.One2many('excel.layout.cell', 'layout_id',
                               string='Layout Cells',
                               help="Individual cell configurations")
    
    # Layout properties
    row_count = fields.Integer('Row Count', compute='_compute_row_count', store=True)
    default_row_height = fields.Integer('Default Row Height', default=20)
    
    # Background
    bg_color = fields.Char('Background Color', help="Background color for entire layout")
    
    active = fields.Boolean('Active', default=True)
    
    @api.depends('cell_ids')
    def _compute_row_count(self):
        for layout in self:
            if layout.cell_ids:
                layout.row_count = max(layout.cell_ids.mapped('row')) + 1
            else:
                layout.row_count = 0
    
    @api.constrains('code')
    def _check_code_unique(self):
        for layout in self:
            if self.search_count([('code', '=', layout.code), ('id', '!=', layout.id)]):
                raise models.ValidationError(_('Layout code must be unique!'))
    
    def render(self, sheet, workbook, data, report_config, start_row=0):
        """Render layout to worksheet"""
        self.ensure_one()
        
        # Apply background color if set
        if self.bg_color:
            format_dict = {'bg_color': self.bg_color}
            bg_format = workbook.add_format(format_dict)
            
            # Apply to all cells in layout
            for cell in self.cell_ids:
                sheet.write(start_row + cell.row, cell.col, '', bg_format)
        
        # Render individual cells
        for cell in self.cell_ids.sorted('row'):
            cell.render(sheet, workbook, data, report_config, start_row)
        
        # Set row heights
        for row in range(self.row_count):
            sheet.set_row(start_row + row, self.default_row_height)
    
    def get_row_count(self):
        """Get the number of rows in this layout"""
        self.ensure_one()
        return self.row_count


class ExcelLayoutCell(models.Model):
    _name = 'excel.layout.cell'
    _description = 'Excel Layout Cell'
    _order = 'layout_id, row, col'

    name = fields.Char('Cell Name', help="Cell identifier for reference")
    
    # Relationships
    layout_id = fields.Many2one('excel.layout', string='Layout', 
                               ondelete='cascade', required=True)
    
    # Position
    row = fields.Integer('Row', required=True, default=0,
                        help="Row index within layout (0-based)")
    col = fields.Integer('Column', required=True, default=0,
                        help="Column index (0-based)")
    
    # Cell content
    content_type = fields.Selection([
        ('static', 'Static Text'),
        ('variable', 'Variable'),
        ('expression', 'Expression'),
        ('empty', 'Empty'),
    ], string='Content Type', required=True, default='static')
    
    static_text = fields.Char('Static Text', help="Static text to display")
    variable_name = fields.Char('Variable Name',
                               help="Variable name (e.g., company_name, report_date)")
    expression = fields.Text('Expression',
                            help="Python expression for dynamic content")
    
    # Merge configuration
    merge_rows = fields.Integer('Merge Rows', default=1,
                               help="Number of rows to merge")
    merge_cols = fields.Integer('Merge Columns', default=1,
                               help="Number of columns to merge")
    
    # Formatting
    format_id = fields.Many2one('excel.cell.format', string='Cell Format',
                               help="Format for this cell")
    
    # Row height override
    row_height = fields.Integer('Row Height', help="Override default row height")
    
    @api.constrains('merge_rows', 'merge_cols')
    def _check_merge_values(self):
        for cell in self:
            if cell.merge_rows < 1:
                raise models.ValidationError(_('Merge rows must be at least 1'))
            if cell.merge_cols < 1:
                raise models.ValidationError(_('Merge columns must be at least 1'))
    
    def render(self, sheet, workbook, data, report_config, start_row=0):
        """Render cell to worksheet"""
        self.ensure_one()
        
        # Get cell content
        content = self._get_content(data, report_config)
        
        # Get cell format
        cell_format = None
        if self.format_id:
            cell_format = self.format_id.get_xlsx_format(workbook)
        
        # Calculate actual position
        actual_row = start_row + self.row
        actual_col = self.col
        
        # Apply merge if needed
        if self.merge_rows > 1 or self.merge_cols > 1:
            sheet.merge_range(
                actual_row, actual_col,
                actual_row + self.merge_rows - 1,
                actual_col + self.merge_cols - 1,
                content, cell_format
            )
        else:
            sheet.write(actual_row, actual_col, content, cell_format)
        
        # Apply row height override
        if self.row_height:
            sheet.set_row(actual_row, self.row_height)
    
    def _get_content(self, data, report_config):
        """Get cell content based on content type"""
        self.ensure_one()
        
        if self.content_type == 'static':
            return self.static_text or ''
        
        elif self.content_type == 'variable':
            return self._get_variable_value(data, report_config)
        
        elif self.content_type == 'expression':
            return self._evaluate_expression(data, report_config)
        
        elif self.content_type == 'empty':
            return ''
        
        return ''
    
    def _get_variable_value(self, data, report_config):
        """Get value of a variable"""
        self.ensure_one()
        
        # Common variables
        variables = {
            'company_name': self.env.company.name,
            'company_logo': '',  # Future: implement logo support
            'report_name': report_config.name,
            'current_date': fields.Date.context_today(self).strftime('%d/%m/%Y'),
            'current_time': fields.Datetime.now().strftime('%H:%M:%S'),
            'user_name': self.env.user.name,
            'timestamp': fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        }
        
        # Add data-based variables
        if data and len(data) > 0:
            variables['record_count'] = len(data)
            variables['first_record'] = data[0] if data else {}
        
        return variables.get(self.variable_name, '')
    
    def _evaluate_expression(self, data, report_config):
        """Evaluate Python expression for dynamic content"""
        self.ensure_one()
        
        if not self.expression:
            return ''
        
        # Prepare evaluation context
        context = {
            'data': data,
            'report': report_config,
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
            # Evaluate expression
            result = eval(self.expression, {'__builtins__': {}}, context)
            return str(result) if result is not None else ''
        except Exception as e:
            return '#ERROR: %s' % str(e)