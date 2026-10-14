# -*- coding: utf-8 -*-

from odoo import models, api, _


class LoadEngine(models.AbstractModel):
    _name = 'connector.load.engine'
    _description = 'Connector Load Engine'
    
    @api.model
    def load_source_data(self, context):
        """
        Load source data from record and populate context variables.
        """
        record = getattr(context, 'record', None)
        if not record:
            return {}
            
        data = {
            'id': record.id,
            'name': getattr(record, 'name', None),
            'display_name': getattr(record, 'display_name', None),
        }
        
        # Load fields into context variables
        for field_name in record._fields:
            if field_name not in data and not field_name.startswith('_'):
                try:
                    data[field_name] = getattr(record, field_name)
                except Exception:
                    pass
                    
        context.set_variable('source_data', data)
        return data
