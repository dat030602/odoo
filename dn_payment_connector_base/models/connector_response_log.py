# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json


class ConnectorResponseLog(models.Model):
    _name = 'connector.response.log'
    _description = 'Connector Response Log'
    _order = 'create_date desc'
    _rec_name = 'display_name'
    
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # References
    execution_id = fields.Many2one('connector.execution', string='Execution', ondelete='cascade')
    request_log_id = fields.Many2one('connector.request.log', string='Request Log', ondelete='cascade')
    provider_id = fields.Many2one('connector.provider', string='Provider', ondelete='restrict')
    api_id = fields.Many2one('connector.api', string='API', ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Response Details
    status_code = fields.Integer(string='Status Code', required=True, index=True)
    status_text = fields.Char(string='Status Text')
    
    # Response Body
    body = fields.Text(string='Response Body')
    body_type = fields.Char(string='Body Type')
    
    # Response Headers
    headers = fields.Text(string='Headers', help='JSON format headers')
    
    # Timing
    response_time = fields.Datetime(string='Response Time', default=fields.Datetime.now, required=True)
    duration = fields.Float(string='Duration (seconds)')
    
    # Success/Failure
    success = fields.Boolean(string='Success', compute='_compute_success', store=True)
    
    # Additional Info
    ip_address = fields.Char(string='IP Address')
    
    @api.depends('api_id.name', 'response_time')
    def _compute_display_name(self):
        for record in self:
            if record.api_id:
                record.display_name = f"{record.api_id.name} - {record.status_code} - {record.response_time}"
            else:
                record.display_name = f"Response - {record.status_code} - {record.response_time}"
    
    @api.depends('status_code')
    def _compute_success(self):
        for record in self:
            record.success = 200 <= record.status_code < 300
    
    def get_headers(self):
        """
        Get headers as dictionary.
        
        Returns:
            Headers dictionary
        """
        self.ensure_one()
        if not self.headers:
            return {}
        
        try:
            return json.loads(self.headers)
        except json.JSONDecodeError:
            return {}
    
    def get_body(self):
        """
        Get response body.
        
        Returns:
            Response body (parsed if JSON)
        """
        self.ensure_one()
        if not self.body:
            return None
        
        if self.body_type == 'JSON':
            try:
                return json.loads(self.body)
            except json.JSONDecodeError:
                return self.body
        
        return self.body
    
    @api.model
    def create_log(self, execution, request_log, status_code, status_text=None, body=None, body_type=None, headers=None, duration=None):
        """
        Create a response log.
        
        Args:
            execution: Execution record
            request_log: Request log record
            status_code: HTTP status code
            status_text: Status text
            body: Response body
            body_type: Body type
            headers: Headers dictionary
            duration: Request duration in seconds
            
        Returns:
            Response log record
        """
        values = {
            'execution_id': execution.id if execution else None,
            'request_log_id': request_log.id if request_log else None,
            'provider_id': execution.provider_id.id if execution else None,
            'api_id': execution.api_id.id if execution else None,
            'status_code': status_code,
            'status_text': status_text,
            'body': body,
            'body_type': body_type,
            'headers': json.dumps(headers) if headers else None,
            'duration': duration,
        }
        
        return self.create(values)
