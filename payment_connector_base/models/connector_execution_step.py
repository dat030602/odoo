# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json


class ConnectorExecutionStep(models.Model):
    _name = 'connector.execution.step'
    _description = 'Connector Execution Step'
    _order = 'execution_id, sequence, create_date'
    
    execution_id = fields.Many2one('connector.execution', string='Execution', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    step_name = fields.Char(string='Step Name', required=True, index=True)
    
    status = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ], string='Status', default='pending', required=True, index=True)
    
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(string='Duration (seconds)', compute='_compute_duration', store=True)
    
    data = fields.Text(string='Data', help='JSON data for this step')
    error_message = fields.Text(string='Error Message')
    error_traceback = fields.Text(string='Error Traceback')
    
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
        Start the step.
        """
        self.write({
            'status': 'running',
            'start_time': fields.Datetime.now(),
        })
    
    def complete(self, success=True, data=None, error_message=None, error_traceback=None):
        """
        Complete the step.
        
        Args:
            success: Whether step was successful
            data: Step data (dict)
            error_message: Error message if failed
            error_traceback: Error traceback if failed
        """
        values = {
            'status': 'success' if success else 'failed',
            'end_time': fields.Datetime.now(),
        }
        
        if data:
            values['data'] = json.dumps(data)
        
        if error_message:
            values['error_message'] = error_message
        
        if error_traceback:
            values['error_traceback'] = error_traceback
        
        self.write(values)
    
    def skip(self):
        """
        Skip the step.
        """
        self.write({
            'status': 'skipped',
            'end_time': fields.Datetime.now(),
        })
    
    def get_data(self):
        """
        Get step data as dictionary.
        
        Returns:
            Data dictionary
        """
        self.ensure_one()
        if not self.data:
            return {}
        
        try:
            return json.loads(self.data)
        except json.JSONDecodeError:
            return {}
