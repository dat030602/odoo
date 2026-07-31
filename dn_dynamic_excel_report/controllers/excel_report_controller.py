# Copyright 2024
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.http import content_disposition, request
from odoo.tools import html_escape


class ExcelReportController(http.Controller):
    """Controller for Excel Report downloads"""

    @http.route('/excel/report/download/<int:report_id>', type='http', auth='user')
    def download_excel_report(self, report_id, **kwargs):
        """
        Download Excel report for given configuration
        
        Args:
            report_id: Excel report configuration ID
            **kwargs: Additional parameters (record IDs, filters, etc.)
            
        Returns:
            HTTP response with Excel file
        """
        report = request.env['excel.report'].browse(report_id)
        if not report.exists():
            return request.not_found()
        
        # Get record IDs from kwargs if provided
        record_ids = kwargs.get('record_ids')
        if record_ids:
            record_ids = [int(rid) for rid in record_ids.split(',')]
            records = request.env[report.model_name].browse(record_ids)
        else:
            records = request.env[report.model_name].search([])
        
        # Generate Excel file
        try:
            excel_content = report.generate_excel(records)
            
            # Generate filename
            filename = self._generate_filename(report, records)
            
            # Return file as response
            return request.make_response(
                excel_content,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', content_disposition(filename)),
                ]
            )
        except Exception as e:
            return request.render(
                'excel_report.error_template',
                {
                    'error': str(e),
                    'report_name': report.name,
                }
            )
    
    @http.route('/excel/report/preview/<int:report_id>', type='http', auth='user')
    def preview_excel_report(self, report_id, **kwargs):
        """
        Preview Excel report with sample data
        
        Args:
            report_id: Excel report configuration ID
            **kwargs: Additional parameters
            
        Returns:
            HTTP response with preview Excel file
        """
        report = request.env['excel.report'].browse(report_id)
        if not report.exists():
            return request.not_found()
        
        # Get limited sample records for preview
        records = request.env[report.model_name].search([], limit=5)
        
        # Generate Excel file
        try:
            excel_content = report.generate_excel(records)
            
            # Generate filename with preview suffix
            filename = f"preview_{self._generate_filename(report, records)}"
            
            # Return file as response
            return request.make_response(
                excel_content,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', content_disposition(filename)),
                ]
            )
        except Exception as e:
            return request.render(
                'excel_report.error_template',
                {
                    'error': str(e),
                    'report_name': report.name,
                }
            )
    
    @http.route('/excel/report/export/<string:model>/<int:report_id>', type='http', auth='user')
    def export_records(self, model, report_id, **kwargs):
        """
        Export selected records using Excel report configuration
        
        Args:
            model: Model name
            report_id: Excel report configuration ID
            **kwargs: Additional parameters including record_ids
            
        Returns:
            HTTP response with Excel file
        """
        report = request.env['excel.report'].browse(report_id)
        if not report.exists():
            return request.not_found()
        
        # Verify model matches
        if report.model_name != model:
            return request.make_response(
                "Model mismatch",
                status=400
            )
        
        # Get record IDs from kwargs
        record_ids = kwargs.get('record_ids')
        if not record_ids:
            return request.make_response(
                "No record IDs provided",
                status=400
            )
        
        record_ids = [int(rid) for rid in record_ids.split(',')]
        records = request.env[model].browse(record_ids)
        
        # Generate Excel file
        try:
            excel_content = report.generate_excel(records)
            
            # Generate filename
            filename = self._generate_filename(report, records)
            
            # Return file as response
            return request.make_response(
                excel_content,
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', content_disposition(filename)),
                ]
            )
        except Exception as e:
            return request.make_response(
                f"Error generating Excel: {str(e)}",
                status=500
            )
    
    def _generate_filename(self, report, records):
        """
        Generate filename for Excel file
        
        Args:
            report: Excel report configuration
            records: Recordset being exported
            
        Returns:
            Generated filename string
        """
        from datetime import datetime
        
        # Get filename pattern from report
        pattern = report.report_file_pattern or 'report_{date}'
        
        # Get current date
        current_date = datetime.now().strftime('%Y%m%d')
        
        # Get company name
        company_name = request.env.company.name.replace(' ', '_')
        
        # Get record count
        record_count = len(records)
        
        # Replace variables in pattern
        filename = pattern.format(
            date=current_date,
            company=company_name,
            report=report.code,
            count=record_count,
        )
        
        # Add extension if not present
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'
        
        return filename