from odoo import api, fields, models


class ExcelReportFormat(models.Model):
    _name = "excel.report.format"
    _description = "Excel Report Format"

    name = fields.Char(string="Format Name", required=True)

    # --- TRƯỜNG TYPE ĐỂ LỰA CHỌN THUỘC TÍNH ĐỊNH DẠNG ---
    type = fields.Selection([
        # Font Properties
        ('font_name', 'Font Name'),
        ('font_size', 'Font Size'),
        ('font_color', 'Font Color'),
        ('bold', 'Bold'),
        ('italic', 'Italic'),
        ('underline', 'Underline'),
        ('font_strikeout', 'Strikeout'),
        ('font_script', 'Superscript/Subscript'),
        # Alignment Properties
        ('align', 'Horizontal Alignment'),
        ('valign', 'Vertical Alignment'),
        ('text_wrap', 'Wrap Text'),
        ('rotation', 'Rotation'),
        ('indent', 'Indent'),
        # Border Properties
        ('border', 'All Borders'),
        ('border_color', 'All Border Color'),
        ('top', 'Top Border'),
        ('top_color', 'Top Border Color'),
        ('bottom', 'Bottom Border'),
        ('bottom_color', 'Bottom Border Color'),
        ('left', 'Left Border'),
        ('left_color', 'Left Border Color'),
        ('right', 'Right Border'),
        ('right_color', 'Right Border Color'),
        # Pattern and Fill Properties
        ('pattern', 'Fill Pattern'),
        ('bg_color', 'Background Color'),
        ('fg_color', 'Foreground Pattern Color'),
        # Number Format & Others
        ('num_format', 'Number Format'),
        ('locked', 'Locked Cell'),
        ('hidden', 'Hide Formulas'),
    ], string="Format Type", required=True, help="Select which format property this record configures")

    # --- 1. FONT PROPERTIES ---
    font_name = fields.Char(string="Font Name", default="Arial")
    font_size = fields.Integer(string="Font Size", default=11)
    font_color = fields.Char(string="Font Color (Hex)", help="E.g., #FF0000 or red")
    bold = fields.Boolean(string="Bold")
    italic = fields.Boolean(string="Italic")
    underline = fields.Selection([
        ('0', 'None'),
        ('1', 'Single Underline'),
        ('2', 'Double Underline'),
        ('33', 'Single Accounting'),
        ('34', 'Double Accounting'),
    ], string="Underline", default='0')
    font_strikeout = fields.Boolean(string="Strikeout (Strikethrough)")
    font_script = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Superscript'),
        ('2', 'Subscript'),
    ], string="Superscript/Subscript", default='0')

    # --- 2. ALIGNMENT PROPERTIES ---
    align = fields.Selection([
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right'),
        ('fill', 'Fill'),
        ('justify', 'Justify'),
        ('center_across', 'Center Across Selection'),
        ('distributed', 'Distributed'),
    ], string="Horizontal Alignment")
    
    valign = fields.Selection([
        ('top', 'Top'),
        ('vcenter', 'Vertical Center'),
        ('bottom', 'Bottom'),
        ('vjustify', 'Vertical Justify'),
        ('vdistributed', 'Vertical Distributed'),
    ], string="Vertical Alignment")

    text_wrap = fields.Boolean(string="Wrap Text")
    rotation = fields.Integer(string="Rotation (Degrees)", help="-90 to 90, or 270 for vertical text")
    indent = fields.Integer(string="Indent Level")

    # --- 3. BORDER PROPERTIES ---
    BORDER_STYLES = [
        ('0', 'None'),
        ('1', 'Thin (------)'),
        ('2', 'Medium (------)'),
        ('3', 'Dashed (- - - -)'),
        ('4', 'Dotted (. . . .)'),
        ('5', 'Thick (------)'),
        ('6', 'Double (======)'),
        ('7', 'Hair (......)'),
        ('8', 'Medium Dashed'),
        ('9', 'Dash Dot'),
        ('10', 'Medium Dash Dot'),
        ('11', 'Dash Dot Dot'),
        ('12', 'Medium Dash Dot Dot'),
        ('13', 'Slanted Dash Dot'),
    ]

    border = fields.Selection(BORDER_STYLES, string="All Borders", default='0')
    border_color = fields.Char(string="All Border Color (Hex)")

    bottom = fields.Selection(BORDER_STYLES, string="Bottom Border", default='0')
    bottom_color = fields.Char(string="Bottom Border Color (Hex)")

    top = fields.Selection(BORDER_STYLES, string="Top Border", default='0')
    top_color = fields.Char(string="Top Border Color (Hex)")

    left = fields.Selection(BORDER_STYLES, string="Left Border", default='0')
    left_color = fields.Char(string="Left Border Color (Hex)")

    right = fields.Selection(BORDER_STYLES, string="Right Border", default='0')
    right_color = fields.Char(string="Right Border Color (Hex)")

    # --- 4. PATTERN AND FILL PROPERTIES ---
    pattern = fields.Selection([
        ('0', 'None'),
        ('1', 'Solid Fill'),
        ('2', 'Medium Gray'),
        ('3', 'Dark Gray'),
        ('4', 'Light Gray'),
        ('5', 'Dark Horizontal Line'),
        ('6', 'Dark Vertical Line'),
        ('7', 'Dark Downward Diagonal'),
        ('8', 'Dark Upward Diagonal'),
        ('9', 'Dark Grid'),
        ('10', 'Dark Trellis'),
    ], string="Fill Pattern", default='0', help="1 is Solid Fill (Most used)")

    bg_color = fields.Char(string="Background Color (Hex)", help="Cell background color (used with solid fill)")
    fg_color = fields.Char(string="Foreground Pattern Color (Hex)")

    # --- 5. NUMBER FORMAT & OTHER PROPERTIES ---
    num_format = fields.Char(string="Number Format", help="E.g. $#,##0.00 or dd/mm/yyyy")
    locked = fields.Boolean(string="Locked Cell", default=True, help="Cell is locked when sheet is protected")
    hidden = fields.Boolean(string="Hide Formulas", default=False, help="Hide formula when sheet is protected")

    def get_format_dict(self):
        format_dict = {}
        for field in self._fields:
            if field not in ['id', 'report_id', 'name', 'type']:
                value = getattr(self, field)
                if value not in [False, None, '', '0']:
                    format_dict[field] = value
        return format_dict
