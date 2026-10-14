# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import base64
import json


class ConnectorAuthMethod(models.Model):
    _name = 'connector.auth.method'
    _description = 'Connector Authentication Method'
    _order = 'name'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, index=True, copy=False)
    type = fields.Selection([
        ('api_key', 'API Key'),
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
        ('jwt', 'JWT'),
        ('oauth2', 'OAuth2'),
        ('hmac', 'HMAC'),
        ('custom', 'Custom'),
    ], string='Type', required=True)
    
    python_class = fields.Char(string='Python Class', help='Custom Python class for authentication')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True, required=True)
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Auth method code must be unique!'),
    ]
    
    def authenticate(self, context=None):
        """
        Generate authentication headers/tokens.
        
        Args:
            context: Connector context object
            
        Returns:
            Dictionary with authentication data (headers, query params, etc.)
        """
        self.ensure_one()
        
        if self.type == 'api_key':
            return self._auth_api_key(context)
        elif self.type == 'basic':
            return self._auth_basic(context)
        elif self.type == 'bearer':
            return self._auth_bearer(context)
        elif self.type == 'jwt':
            return self._auth_jwt(context)
        elif self.type == 'oauth2':
            return self._auth_oauth2(context)
        elif self.type == 'hmac':
            return self._auth_hmac(context)
        elif self.type == 'custom':
            return self._auth_custom(context)
        
        return {}
    
    def _auth_api_key(self, context):
        """
        API Key authentication.
        
        Args:
            context: Connector context object
            
        Returns:
            Headers dictionary
        """
        if not context or not hasattr(context, 'provider'):
            return {}
        
        api_key = context.provider.get_setting('api_key')
        key_name = context.provider.get_setting('api_key_name') or 'X-API-Key'
        
        if not api_key:
            return {}
        
        return {'headers': {key_name: api_key}}
    
    def _auth_basic(self, context):
        """
        Basic authentication.
        
        Args:
            context: Connector context object
            
        Returns:
            Headers dictionary
        """
        if not context or not hasattr(context, 'provider'):
            return {}
        
        username = context.provider.get_setting('username')
        password = context.provider.get_setting('password')
        
        if not username or not password:
            return {}
        
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        return {'headers': {'Authorization': f'Basic {encoded}'}}
    
    def _auth_bearer(self, context):
        """
        Bearer token authentication.
        
        Args:
            context: Connector context object
            
        Returns:
            Headers dictionary
        """
        if not context or not hasattr(context, 'provider'):
            return {}
        
        token = context.provider.get_setting('bearer_token')
        
        if not token:
            return {}
        
        return {'headers': {'Authorization': f'Bearer {token}'}}
    
    def _auth_jwt(self, context):
        """
        JWT authentication.
        
        Args:
            context: Connector context object
            
        Returns:
            Headers dictionary
        """
        if not context or not hasattr(context, 'provider'):
            return {}
        
        token = context.provider.get_setting('jwt_token')
        
        if not token:
            return {}
        
        return {'headers': {'Authorization': f'Bearer {token}'}}
    
    def _auth_oauth2(self, context):
        """
        OAuth2 authentication.
        
        Args:
            context: Connector context object
            
        Returns:
            Headers dictionary
        """
        if not context or not hasattr(context, 'provider'):
            return {}
        
        access_token = context.provider.get_setting('oauth_access_token')
        
        if not access_token:
            return {}
        
        return {'headers': {'Authorization': f'Bearer {access_token}'}}
    
    def _auth_hmac(self, context):
        """
        HMAC authentication.
        
        Args:
            context: Connector context object
            
        Returns:
            Headers dictionary
        """
        if not context or not hasattr(context, 'provider'):
            return {}
        
        api_key = context.provider.get_setting('hmac_api_key')
        api_secret = context.provider.get_setting('hmac_api_secret')
        
        if not api_key or not api_secret:
            return {}
        
        return {'headers': {'X-API-Key': api_key, 'X-API-Secret': api_secret}}
    
    def _auth_custom(self, context):
        """
        Custom authentication using Python class.
        
        Args:
            context: Connector context object
            
        Returns:
            Headers dictionary
        """
        if not self.python_class:
            return {}
        
        try:
            module_path, class_name = self.python_class.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            auth_class = getattr(module, class_name)
            auth_instance = auth_class()
            return auth_instance.authenticate(context)
        except Exception:
            return {}
