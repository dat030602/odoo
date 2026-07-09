# -*- coding: utf-8 -*-

from odoo import models, api, _


class HTTPEngine(models.AbstractModel):
    _name = 'connector.http.engine'
    _description = 'Connector HTTP Engine'
    
    @api.model
    def send_request(self, context):
        """
        Send HTTP request.
        
        Args:
            context: ConnectorContext object
            
        Returns:
            Dictionary with response data
        """
        # Implementation will be added later
        return {}
