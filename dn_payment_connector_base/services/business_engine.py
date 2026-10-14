# -*- coding: utf-8 -*-

from odoo import models, api, _


class BusinessEngine(models.AbstractModel):
    _name = 'connector.business.engine'
    _description = 'Connector Business Engine'
    
    @api.model
    def execute_actions(self, context, response_data):
        """
        Execute post-response business actions / plugins.
        """
        provider = getattr(context, 'provider', None)
        if not provider:
            return {}
            
        results = {}
        for plugin in provider.plugin_ids.filtered(lambda p: p.active):
            try:
                results[plugin.code] = plugin.execute(context, response_data)
            except Exception as e:
                results[plugin.code] = {'error': str(e)}
        return results
