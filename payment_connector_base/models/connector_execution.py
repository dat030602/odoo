# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
import json


class ConnectorExecution(models.Model):
    _name = 'connector.execution'
    _description = 'Connector Execution'
    _order = 'create_date desc'
    _rec_name = 'display_name'
    
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # References
    provider_id = fields.Many2one('connector.provider', string='Provider', required=True, ondelete='restrict')
    api_id = fields.Many2one('connector.api', string='API', required=True, ondelete='restrict')
    endpoint_id = fields.Many2one('connector.endpoint', string='Endpoint', ondelete='restrict')
    environment_id = fields.Many2one('connector.environment', string='Environment', ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Source Record
    res_model = fields.Char(string='Source Model', help='Odoo model of source record')
    res_id = fields.Integer(string='Source ID', help='ID of source record')
    
    # Execution Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='pending', required=True, index=True)
    
    # Timing
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(string='Duration (seconds)', compute='_compute_duration', store=True)
    
    # Retry
    retry_count = fields.Integer(string='Retry Count', default=0)
    max_retry = fields.Integer(string='Max Retry', default=3)
    
    # Error
    error_message = fields.Text(string='Error Message')
    error_traceback = fields.Text(string='Error Traceback')
    
    # Response Data
    response_status_code = fields.Integer(string='Response Status Code')
    response_body = fields.Text(string='Response Body')
    
    # Execution Mode
    mode = fields.Selection([
        ('sync', 'Synchronous'),
        ('async', 'Asynchronous'),
        ('schedule', 'Scheduled'),
    ], string='Execution Mode', default='sync', required=True)
    
    # Relations
    step_ids = fields.One2many('connector.execution.step', 'execution_id', string='Execution Steps')
    request_log_id = fields.Many2one('connector.request.log', string='Request Log', ondelete='set null')
    response_log_id = fields.Many2one('connector.response.log', string='Response Log', ondelete='set null')
    error_log_id = fields.Many2one('connector.error.log', string='Error Log', ondelete='set null')
    
    # Computed fields for stat buttons
    step_count = fields.Integer(string='Step Count', compute='_compute_step_count')
    
    @api.depends('step_ids')
    def _compute_step_count(self):
        for record in self:
            record.step_count = len(record.step_ids)
    
    def action_view_steps(self):
        """
        Action to view execution steps.
        """
        self.ensure_one()
        return {
            'name': _('Execution Steps'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.execution.step',
            'view_mode': 'tree,form',
            'domain': [('execution_id', '=', self.id)],
            'context': {'default_execution_id': self.id}
        }
    
    @api.depends('api_id.name', 'create_date')
    def _compute_display_name(self):
        for record in self:
            if record.api_id:
                record.display_name = f"{record.api_id.name} - {record.create_date}"
            else:
                record.display_name = f"Execution - {record.create_date}"
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration = delta.total_seconds()
            else:
                record.duration = 0.0
    
    def start(self):
        """
        Start the execution.
        """
        self.write({
            'state': 'running',
            'start_time': fields.Datetime.now(),
        })
    
    def complete(self, success=True, error_message=None, response_status_code=None, response_body=None):
        """
        Complete the execution.
        
        Args:
            success: Whether execution was successful
            error_message: Error message if failed
            response_status_code: HTTP response status code
            response_body: Response body
        """
        values = {
            'state': 'success' if success else 'failed',
            'end_time': fields.Datetime.now(),
        }
        
        if error_message:
            values['error_message'] = error_message
        
        if response_status_code:
            values['response_status_code'] = response_status_code
        
        if response_body:
            values['response_body'] = response_body
        
        self.write(values)
    
    def cancel(self):
        """
        Cancel the execution.
        """
        self.write({
            'state': 'cancelled',
            'end_time': fields.Datetime.now(),
        })
    
    def retry(self):
        """
        Retry the execution.
        """
        for record in self:
            if record.retry_count < record.max_retry:
                record.write({
                    'retry_count': record.retry_count + 1,
                    'state': 'pending',
                    'error_message': None,
                    'error_traceback': None,
                })
                # Trigger retry logic here
                # This will be implemented by the execution engine
    
    def get_source_record(self):
        """
        Get the source record for this execution.
        
        Returns:
            Source record or None
        """
        self.ensure_one()
        if self.res_model and self.res_id:
            return self.env[self.res_model].browse(self.res_id)
        return None
    
    def add_step(self, step_name, status='success', duration=0.0, data=None, error_message=None):
        """
        Add an execution step.
        
        Args:
            step_name: Name of the step
            status: Status of the step (success, failed, skipped)
            duration: Duration in seconds
            data: Step data (dict)
            error_message: Error message if failed
            
        Returns:
            Execution step record
        """
        self.ensure_one()
        
        return self.env['connector.execution.step'].create({
            'execution_id': self.id,
            'step_name': step_name,
            'status': status,
            'duration': duration,
            'data': json.dumps(data) if data else None,
            'error_message': error_message,
        })
    
    def get_execution_summary(self):
        """
        Get a summary of the execution.
        
        Returns:
            Dictionary with execution summary
        """
        self.ensure_one()
        
        steps_summary = {}
        for step in self.step_ids:
            if step.step_name not in steps_summary:
                steps_summary[step.step_name] = {
                    'count': 0,
                    'success': 0,
                    'failed': 0,
                    'total_duration': 0.0,
                }
            
            steps_summary[step.step_name]['count'] += 1
            steps_summary[step.step_name]['total_duration'] += step.duration
            
            if step.status == 'success':
                steps_summary[step.step_name]['success'] += 1
            elif step.status == 'failed':
                steps_summary[step.step_name]['failed'] += 1
        
        return {
            'execution_id': self.id,
            'state': self.state,
            'duration': self.duration,
            'retry_count': self.retry_count,
            'steps': steps_summary,
        }
