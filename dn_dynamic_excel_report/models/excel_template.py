# Copyright 2024
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _


class ExcelTemplate(models.Model):
    _name = 'excel.template'
    _description = 'Excel Report Template'
    _order = 'name, id'

    name = fields.Char('Template Name', required=True, translate=True)
    code = fields.Char('Template Code', required=True, help="Technical identifier for the template")
    description = fields.Text('Description', help="Template description for users")
    
    # Default configurations
    default_header_layout_id = fields.Many2one('excel.layout', string='Default Header Layout',
                                               domain=[('layout_type', '=', 'header')])
    default_body_layout_ids = fields.Many2many('excel.layout', 'template_body_layout_rel',
                                               'template_id', 'layout_id',
                                               string='Default Body Layouts',
                                               domain=[('layout_type', '=', 'body')])
    default_footer_layout_id = fields.Many2one('excel.layout', string='Default Footer Layout',
                                               domain=[('layout_type', '=', 'footer')])
    
    # Default column configuration
    default_column_ids = fields.One2many('excel.column.config', 'template_id',
                                         string='Default Column Configuration')
    
    # Default settings
    default_sheet_name = fields.Char('Default Sheet Name', default='Report')
    default_file_pattern = fields.Char('Default File Pattern', default='report_{date}')
    default_auto_filter = fields.Boolean('Default Auto Filter', default=True)
    default_freeze_panes = fields.Boolean('Default Freeze Panes', default=True)
    default_header_height = fields.Integer('Default Header Height', default=25)
    default_data_height = fields.Integer('Default Data Height', default=20)
    
    # Usage tracking
    report_ids = fields.One2many('excel.report', 'template_id', string='Reports Using Template')
    report_count = fields.Integer('Report Count', compute='_compute_report_count')
    
    active = fields.Boolean('Active', default=True)
    
    @api.depends('report_ids')
    def _compute_report_count(self):
        for template in self:
            template.report_count = len(template.report_ids)
    
    @api.constrains('code')
    def _check_code_unique(self):
        for template in self:
            if self.search_count([('code', '=', template.code), ('id', '!=', template.id)]):
                raise models.ValidationError(_('Template code must be unique!'))
    
    def apply_to_report(self, report_id):
        """Apply template to a report"""
        self.ensure_one()
        report = self.env['excel.report'].browse(report_id)
        
        if not report.exists():
            raise models.ValidationError(_('Report not found'))
        
        # Apply template configurations
        report.write({
            'sheet_name': self.default_sheet_name,
            'report_file_pattern': self.default_file_pattern,
            'auto_filter': self.default_auto_filter,
            'freeze_panes': self.default_freeze_panes,
            'header_row_height': self.default_header_height,
            'data_row_height': self.default_data_height,
            'header_layout_id': self.default_header_layout_id.id if self.default_header_layout_id else False,
            'footer_layout_id': self.default_footer_layout_id.id if self.default_footer_layout_id else False,
        })
        
        # Apply body layouts
        if self.default_body_layout_ids:
            report.body_layout_ids = [(6, 0, self.default_body_layout_ids.ids)]
        
        # Apply column configurations
        if self.default_column_ids:
            # Copy default columns to report
            for default_col in self.default_column_ids:
                default_col.copy({
                    'report_id': report.id,
                    'template_id': False,
                })
        
        return True