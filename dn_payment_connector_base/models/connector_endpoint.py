# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ConnectorEndpoint(models.Model):
    _name = 'connector.endpoint'
    _description = 'Connector API Endpoint'
    _order = 'sequence, name'
    
    name = fields.Char(string='Name', required=True)
    api_id = fields.Many2one('connector.api', string='API', required=True, ondelete='cascade')
    provider_id = fields.Many2one(related='api_id.provider_id', string='Provider', store=True, readonly=True)
    environment_id = fields.Many2one('connector.environment', string='Environment', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    execution_type = fields.Selection([
        ('api_call', 'API Call (POST/PUT/PATCH/DELETE)'),
        ('redirect', 'Redirect URL (GET with query params)'),
        ('webhook', 'Webhook Receiver'),
    ], string='Execution Type', default='api_call')
    
    hash_param_name = fields.Char(
        string='Hash Parameter Name',
        default='vnp_SecureHash',
        help='Name of the hash/signature parameter in the URL or body'
    )
    
    secret_setting_code = fields.Char(
        string='Secret Setting Code',
        default='hash_secret',
        help='Setting code for the hash secret key'
    )
    
    # HTTP Configuration
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ], string='HTTP Method', required=True, default='POST')
    
    url = fields.Char(string='URL', required=True, help='Full URL or path relative to environment base URL')
    timeout = fields.Integer(string='Timeout (seconds)', default=30)
    retry = fields.Integer(string='Retry Count', default=3)
    
    # Request Configuration
    body_type = fields.Selection([
        ('JSON', 'JSON'),
        ('XML', 'XML'),
        ('FORM', 'Form Data'),
        ('MULTIPART', 'Multipart'),
        ('RAW', 'Raw'),
        ('NONE', 'None'),
    ], string='Body Type', default='JSON')
    
    # Response Configuration
    parser = fields.Selection([
        ('JSON', 'JSON'),
        ('XML', 'XML'),
        ('CSV', 'CSV'),
        ('TEXT', 'Text'),
        ('HTML', 'HTML'),
    ], string='Response Parser', default='JSON')
    
    # Authentication
    auth_method_id = fields.Many2one('connector.auth.method', string='Authentication Method')
    
    # Hash/Signature
    hash_method_id = fields.Many2one('connector.hash.method', string='Hash Method')
    
    active = fields.Boolean(string='Active', default=True, required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    
    _sql_constraints = [
        ('api_env_company_unique', 
         'UNIQUE(api_id, environment_id, company_id)', 
         'Endpoint must be unique per API, environment, and company!'),
    ]
    
    def get_full_url(self):
        self.ensure_one()
        base_url = self.environment_id.get_base_url()
        url = self.url or ''
        if not url.startswith(('http://', 'https://')):
            url = base_url.rstrip('/') + '/' + url.lstrip('/')
        return url
    
    def get_headers(self, context=None):
        self.ensure_one()
        header_mapping = self.api_id.get_mapping('HEADER')
        if header_mapping:
            return header_mapping.build_dict(context)
        return {}
    
    def get_payload(self, context=None):
        self.ensure_one()
        payload_mapping = self.api_id.get_mapping('PAYLOAD')
        if payload_mapping:
            return payload_mapping.build_dict(context)
        return {}
    
    def get_query_params(self, context=None):
        self.ensure_one()
        query_mapping = self.api_id.get_mapping('QUERY')
        if query_mapping:
            return query_mapping.build_dict(context)
        return {}
