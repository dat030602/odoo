# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import traceback


class ConnectorErrorLog(models.Model):
    _name = 'connector.error.log'
    _description = 'Connector Error Log'
    _order = 'create_date desc'
    _rec_name = 'display_name'
    
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # References
    execution_id = fields.Many2one('connector.execution', string='Execution', ondelete='cascade')
    execution_step_id = fields.Many2one('connector.execution.step', string='Execution Step', ondelete='cascade')
    request_log_id = fields.Many2one('connector.request.log', string='Request Log', ondelete='cascade')
    response_log_id = fields.Many2one('connector.response.log', string='Response Log', ondelete='cascade')
    provider_id = fields.Many2one('connector.provider', string='Provider', ondelete='restrict')
    api_id = fields.Many2one('connector.api', string='API', ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Error Details
    error_type = fields.Char(string='Error Type', required=True, index=True)
    error_message = fields.Text(string='Error Message', required=True)
    error_traceback = fields.Text(string='Error Traceback')
    
    # Step Information
    step_name = fields.Char(string='Step Name', help='Step where error occurred')
    
    # Error Severity
    severity = fields.Selection([
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ], string='Severity', default='error', required=True, index=True)
    
    # Timing
    error_time = fields.Datetime(string='Error Time', default=fields.Datetime.now, required=True)
    
    # Additional Info
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    ip_address = fields.Char(string='IP Address')
    
    # Stack Trace
    stack_trace = fields.Text(string='Stack Trace')
    
    @api.depends('error_type', 'error_time')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.error_type} - {record.error_time}"
    
    @api.model
    def create_log(self, execution, error_type, error_message, error_traceback=None, step_name=None, severity='error'):
        """
        Create an error log.
        
        Args:
            execution: Execution record
            error_type: Type of error
            error_message: Error message
            error_traceback: Error traceback
            step_name: Step where error occurred
            severity: Error severity
            
        Returns:
            Error log record
        """
        values = {
            'execution_id': execution.id if execution else None,
            'provider_id': execution.provider_id.id if execution else None,
            'api_id': execution.api_id.id if execution else None,
            'error_type': error_type,
            'error_message': error_message,
            'error_traceback': error_traceback,
            'step_name': step_name,
            'severity': severity,
            'stack_trace': traceback.format_exc() if error_traceback else None,
        }
        
        return self.create(values)
    
    def get_formatted_error(self):
        """
        Get formatted error message.
        
        Returns:
            Formatted error string
        """
        self.ensure_one()
        
        parts = [f"[{self.severity.upper()}] {self.error_type}"]
        
        if self.step_name:
            parts.append(f"Step: {self.step_name}")
        
        parts.append(f"Message: {self.error_message}")
        
        if self.error_traceback:
            parts.append(f"Traceback:\n{self.error_traceback}")
        
        return '\n'.join(parts)
