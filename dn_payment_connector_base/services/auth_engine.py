# -*- coding: utf-8 -*-

from odoo import models, api, _


class AuthEngine(models.AbstractModel):
    _name = 'connector.auth.engine'
    _description = 'Connector Authentication Engine'
    
    @api.model
    def authenticate(self, context):
        """
        Generate authentication using endpoint's auth_method_id.
        """
        endpoint = getattr(context, 'endpoint', None)
        if not endpoint or not endpoint.auth_method_id:
            return {}
            
        auth_data = endpoint.auth_method_id.authenticate(context)
        context.set_variable('auth_data', auth_data)
        
        # Merge headers if auth generates headers
        if auth_data and isinstance(auth_data, dict):
            current_headers = context.get_variable('headers') or {}
            current_headers.update(auth_data.get('headers', {}))
            context.set_variable('headers', current_headers)
            
        return auth_data or {}
