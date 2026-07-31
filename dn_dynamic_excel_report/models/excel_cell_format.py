# Copyright 2024
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _


class ExcelCellFormat(models.Model):
    _name = 'excel.cell.format'
    _description = 'Excel Cell Format'
    _order = 'name, id'

    name = fields.Char('Format Name', required=True, translate=True)
    code = fields.Char('Format Code', required=True, help="Technical identifier for the format")
    description = fields.Text('Description', help="Format description for users")
    
    # Font settings
    font_name = fields.Char('Font Name', default='Arial', help="Font family")
    font_size = fields.Integer('Font Size', default=11, help="Font size in points")
    font_bold = fields.Boolean('Bold', default=False)
    font_italic = fields.Boolean('Italic', default=False)
    font_underline = fields.Boolean('Underline', default=False)
    font_color = fields.Char('Font Color', default='#000000', help="Hex color code")
    
    # Alignment
    horizontal_align = fields.Selection([
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right'),
        ('fill', 'Fill'),
        ('justify', 'Justify'),
        ('center_continuous', 'Center Continuous'),
    ], string='Horizontal Alignment', default='left')
    
    vertical_align = fields.Selection([
        ('top', 'Top'),
        ('center', 'Center'),
        ('bottom', 'Bottom'),
        ('vjustify', 'Vertical Justify'),
    ], string='Vertical Alignment', default='center')
    
    text_wrap = fields.Boolean('Text Wrap', default=False, help="Wrap text in cells")
    rotation = fields.Integer('Rotation', default=0, help="Text rotation angle (-90 to 90)")
    indent = fields.Integer('Indent', default=0, help="Text indentation")
    shrink_to_fit = fields.Boolean('Shrink to Fit', default=False)
    
    # Background
    bg_color = fields.Char('Background Color', help="Hex color code for background")
    bg_pattern = fields.Selection([
        ('none', 'None'),
        ('solid', 'Solid'),
        ('mediumGray', 'Medium Gray'),
        ('darkGray', 'Dark Gray'),
        ('lightGray', 'Light Gray'),
        ('darkHorizontal', 'Dark Horizontal'),
        ('darkVertical', 'Dark Vertical'),
        ('darkDown', 'Dark Down'),
        ('darkUp', 'Dark Up'),
        ('darkGrid', 'Dark Grid'),
        ('darkTrellis', 'Dark Trellis'),
        ('lightHorizontal', 'Light Horizontal'),
        ('lightVertical', 'Light Vertical'),
        ('lightDown', 'Light Down'),
        ('lightUp', 'Light Up'),
        ('lightGrid', 'Light Grid'),
        ('lightTrellis', 'Light Trellis'),
        ('gray125', 'Gray 125%'),
        ('gray0625', 'Gray 6.25%'),
    ], string='Background Pattern', default='none')
    
    # Borders
    border_left = fields.Selection([
        ('none', 'None'),
        ('thin', 'Thin'),
        ('medium', 'Medium'),
        ('dashed', 'Dashed'),
        ('dotted', 'Dotted'),
        ('thick', 'Thick'),
        ('double', 'Double'),
        ('hair', 'Hair'),
        ('medium_dashed', 'Medium Dashed'),
        ('dash_dot', 'Dash Dot'),
        ('medium_dash_dot', 'Medium Dash Dot'),
        ('dash_dot_dot', 'Dash Dot Dot'),
        ('medium_dash_dot_dot', 'Medium Dash Dot Dot'),
        ('slant_dash_dot', 'Slant Dash Dot'),
    ], string='Left Border', default='none')
    
    border_right = fields.Selection([
        ('none', 'None'),
        ('thin', 'Thin'),
        ('medium', 'Medium'),
        ('dashed', 'Dashed'),
        ('dotted', 'Dotted'),
        ('thick', 'Thick'),
        ('double', 'Double'),
        ('hair', 'Hair'),
        ('medium_dashed', 'Medium Dashed'),
        ('dash_dot', 'Dash Dot'),
        ('medium_dash_dot', 'Medium Dash Dot'),
        ('dash_dot_dot', 'Dash Dot Dot'),
        ('medium_dash_dot_dot', 'Medium Dash Dot Dot'),
        ('slant_dash_dot', 'Slant Dash Dot'),
    ], string='Right Border', default='none')
    
    border_top = fields.Selection([
        ('none', 'None'),
        ('thin', 'Thin'),
        ('medium', 'Medium'),
        ('dashed', 'Dashed'),
        ('dotted', 'Dotted'),
        ('thick', 'Thick'),
        ('double', 'Double'),
        ('hair', 'Hair'),
        ('medium_dashed', 'Medium Dashed'),
        ('dash_dot', 'Dash Dot'),
        ('medium_dash_dot', 'Medium Dash Dot'),
        ('dash_dot_dot', 'Dash Dot Dot'),
        ('medium_dash_dot_dot', 'Medium Dash Dot Dot'),
        ('slant_dash_dot', 'Slant Dash Dot'),
    ], string='Top Border', default='none')
    
    border_bottom = fields.Selection([
        ('none', 'None'),
        ('thin', 'Thin'),
        ('medium', 'Medium'),
        ('dashed', 'Dashed'),
        ('dotted', 'Dotted'),
        ('thick', 'Thick'),
        ('double', 'Double'),
        ('hair', 'Hair'),
        ('medium_dashed', 'Medium Dashed'),
        ('dash_dot', 'Dash Dot'),
        ('medium_dash_dot', 'Medium Dash Dot'),
        ('dash_dot_dot', 'Dash Dot Dot'),
        ('medium_dash_dot_dot', 'Medium Dash Dot Dot'),
        ('slant_dash_dot', 'Slant Dash Dot'),
    ], string='Bottom Border', default='none')
    
    border_left_color = fields.Char('Left Border Color', default='#000000')
    border_right_color = fields.Char('Right Border Color', default='#000000')
    border_top_color = fields.Char('Top Border Color', default='#000000')
    border_bottom_color = fields.Char('Bottom Border Color', default='#000000')
    
    # Number format
    number_format = fields.Char('Number Format', help="Excel number format code")
    num_format_category = fields.Selection([
        ('general', 'General'),
        ('number', 'Number'),
        ('currency', 'Currency'),
        ('accounting', 'Accounting'),
        ('short_date', 'Short Date'),
        ('long_date', 'Long Date'),
        ('time', 'Time'),
        ('percentage', 'Percentage'),
        ('fraction', 'Fraction'),
        ('scientific', 'Scientific'),
        ('text', 'Text'),
        ('custom', 'Custom'),
    ], string='Number Format Category', default='general')
    
    # Protection
    locked = fields.Boolean('Locked', default=True, help="Cell is locked when sheet is protected")
    hidden = fields.Boolean('Hidden', default=False, help="Formula is hidden when sheet is protected")
    
    # Usage
    header_format_usage = fields.One2many('excel.column.config', 'header_format_id', 
                                         string='Used as Header Format')
    cell_format_usage = fields.One2many('excel.column.config', 'cell_format_id',
                                       string='Used as Cell Format')
    summary_format_usage = fields.One2many('excel.column.config', 'summary_format_id',
                                          string='Used as Summary Format')
    layout_cell_usage = fields.One2many('excel.layout.cell', 'format_id',
                                       string='Used in Layout Cells')
    
    active = fields.Boolean('Active', default=True)
    
    @api.constrains('code')
    def _check_code_unique(self):
        for fmt in self:
            if self.search_count([('code', '=', fmt.code), ('id', '!=', fmt.id)]):
                raise models.ValidationError(_('Format code must be unique!'))
    
    def get_xlsx_format(self, workbook):
        """Get xlsxwriter format object"""
        self.ensure_one()
        format_dict = {}
        
        # Font settings
        if self.font_name:
            format_dict['font_name'] = self.font_name
        if self.font_size:
            format_dict['font_size'] = self.font_size
        if self.font_bold:
            format_dict['bold'] = True
        if self.font_italic:
            format_dict['italic'] = True
        if self.font_underline:
            format_dict['underline'] = True
        if self.font_color:
            format_dict['font_color'] = self.font_color
        
        # Alignment
        if self.horizontal_align:
            format_dict['align'] = self.horizontal_align
        if self.vertical_align:
            format_dict['valign'] = self.vertical_align
        if self.text_wrap:
            format_dict['text_wrap'] = True
        if self.rotation:
            format_dict['rotation'] = self.rotation
        if self.indent:
            format_dict['indent'] = self.indent
        if self.shrink_to_fit:
            format_dict['shrink'] = True
        
        # Background
        if self.bg_color:
            format_dict['bg_color'] = self.bg_color
        if self.bg_pattern and self.bg_pattern != 'none':
            format_dict['pattern'] = self.bg_pattern
        
        # Borders
        border_dict = {}
        if self.border_left and self.border_left != 'none':
            border_dict['left'] = self.border_left
        if self.border_right and self.border_right != 'none':
            border_dict['right'] = self.border_right
        if self.border_top and self.border_top != 'none':
            border_dict['top'] = self.border_top
        if self.border_bottom and self.border_bottom != 'none':
            border_dict['bottom'] = self.border_bottom
        
        if border_dict:
            format_dict['border'] = border_dict
        
        # Border colors
        if self.border_left_color and self.border_left != 'none':
            format_dict['left_color'] = self.border_left_color
        if self.border_right_color and self.border_right != 'none':
            format_dict['right_color'] = self.border_right_color
        if self.border_top_color and self.border_top != 'none':
            format_dict['top_color'] = self.border_top_color
        if self.border_bottom_color and self.border_bottom != 'none':
            format_dict['bottom_color'] = self.border_bottom_color
        
        # Number format
        if self.number_format:
            format_dict['num_format'] = self.number_format
        elif self.num_format_category != 'general':
            format_dict['num_format'] = self._get_predefined_num_format()
        
        # Protection
        if not self.locked:
            format_dict['locked'] = False
        if self.hidden:
            format_dict['hidden'] = True
        
        return workbook.add_format(format_dict)
    
    def _get_predefined_num_format(self):
        """Get predefined number format based on category"""
        self.ensure_one()
        formats = {
            'number': '#,##0.00',
            'currency': '#,##0.00 [$€-1]',
            'accounting': '_("$"* #,##0.00_);_("$"* \(#,##0.00\);_("$"* "-"??_);_(@_)',
            'short_date': 'dd/mm/yyyy',
            'long_date': 'dddd, mmmm dd, yyyy',
            'time': 'hh:mm:ss',
            'percentage': '0.00%',
            'fraction': '# ?/?',
            'scientific': '0.00E+00',
            'text': '@',
        }
        return formats.get(self.num_format_category, 'general')
    
    def duplicate_format(self):
        """Duplicate this format"""
        self.ensure_one()
        return self.copy({
            'name': _('%s (copy)') % self.name,
            'code': '%s_copy' % self.code,
        })