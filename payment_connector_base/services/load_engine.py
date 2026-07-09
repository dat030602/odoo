# -*- coding: utf-8 -*-

from odoo import models, api, _


class LoadEngine(models.AbstractModel):
    _name = 'connector.load.engine'
    _description = 'Connector Load Engine'
    
    @api.model
    def load_source_data(self, context):
        """
        Load source data from record.
        
        Args:
            context: ConnectorContext object
            
        Returns:
            Dictionary of source data
        """
        # Implementation will be added later
        return {}
