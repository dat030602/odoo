# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json


class ConnectorRequestLog(models.Model):
    _name = 'connector.request.log'
    _description = 'Connector Request Log'
    _order = 'create_date desc'
    _rec_name = 'display_name'
    
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # References
    execution_id = fields.Many2one('connector.execution', string='Execution', ondelete='cascade')
    provider_id = fields.Many2one('connector.provider', string='Provider', ondelete='restrict')
    api_id = fields.Many2one('connector.api', string='API', ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Request Details
    method = fields.Char(string='HTTP Method', required=True)
    url = fields.Char(string='URL', required=True)
    
    # Headers
    headers = fields.Text(string='Headers', help='JSON format headers')
    
    # Request Body
    body = fields.Text(string='Request Body')
    body_type = fields.Char(string='Body Type')
    
    # Query Parameters
    query_params = fields.Text(string='Query Parameters', help='JSON format query parameters')
    
    # Authentication
    auth_method = fields.Char(string='Authentication Method')
    
    # Timing
    request_time = fields.Datetime(string='Request Time', default=fields.Datetime.now, required=True)
    
    # Additional Info
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    ip_address = fields.Char(string='IP Address')
    
    @api.depends('api_id.name', 'request_time')
    def _compute_display_name(self):
        for record in self:
            if record.api_id:
                record.display_name = f"{record.api_id.name} - {record.request_time}"
            else:
                record.display_name = f"Request - {record.request_time}"
    
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
    
    def get_query_params(self):
        """
        Get query parameters as dictionary.
        
        Returns:
            Query parameters dictionary
        """
        self.ensure_one()
        if not self.query_params:
            return {}
        
        try:
            return json.loads(self.query_params)
        except json.JSONDecodeError:
            return {}
    
    def get_body(self):
        """
        Get request body.
        
        Returns:
            Request body (parsed if JSON)
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
    def create_log(self, execution, method, url, headers=None, body=None, body_type=None, query_params=None, auth_method=None):
        """
        Create a request log.
        
        Args:
            execution: Execution record
            method: HTTP method
            url: Request URL
            headers: Headers dictionary
            body: Request body
            body_type: Body type
            query_params: Query parameters dictionary
            auth_method: Authentication method
            
        Returns:
            Request log record
        """
        values = {
            'execution_id': execution.id if execution else None,
            'provider_id': execution.provider_id.id if execution else None,
            'api_id': execution.api_id.id if execution else None,
            'method': method,
            'url': url,
            'headers': json.dumps(headers) if headers else None,
            'body': body,
            'body_type': body_type,
            'query_params': json.dumps(query_params) if query_params else None,
            'auth_method': auth_method,
        }
        
        return self.create(values)
