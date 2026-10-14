# -*- coding: utf-8 -*-

from odoo import models, api, _
import json
import csv
import io


class ResponseEngine(models.AbstractModel):
    _name = 'connector.response.engine'
    _description = 'Connector Response Engine'
    
    @api.model
    def parse_response(self, context, raw_response):
        """
        Parse HTTP response based on endpoint parser.
        """
        endpoint = getattr(context, 'endpoint', None)
        parser = endpoint.parser if endpoint else 'JSON'
        
        body = raw_response.get('response_body', '')
        parsed = {}
        
        if not body:
            return {}
            
        try:
            if parser == 'JSON':
                parsed = json.loads(body)
            elif parser == 'TEXT':
                parsed = {'raw_text': body}
            elif parser == 'CSV':
                reader = csv.DictReader(io.StringIO(body))
                parsed = {'rows': list(reader)}
            elif parser == 'HTML' or parser == 'XML':
                parsed = {'raw': body}
        except Exception as e:
            parsed = {'parse_error': str(e), 'raw': body}
            
        context.set_variable('response_data', parsed)
        return parsed
