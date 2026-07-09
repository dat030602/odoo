# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json


class ConnectorComputePipeline(models.Model):
    _name = 'connector.compute.pipeline'
    _description = 'Connector Compute Pipeline'
    _order = 'mapping_line_id, sequence'
    
    mapping_line_id = fields.Many2one('connector.mapping.line', string='Mapping Line', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', required=True, default=10)
    function_id = fields.Many2one('connector.compute.function', string='Function', required=True)
    parameter_json = fields.Text(string='Parameters', help='JSON format parameters for the function')
    stop_if_none = fields.Boolean(string='Stop if None', default=False, help='Stop pipeline if function returns None')
    description = fields.Text(string='Description')
    
    def get_parameters(self):
        """
        Get parameters as dictionary.
        
        Returns:
            Parameters dictionary
        """
        self.ensure_one()
        if not self.parameter_json:
            return {}
        
        try:
            return json.loads(self.parameter_json)
        except json.JSONDecodeError:
            return {}
    
    def execute(self, value, context=None):
        """
        Execute this pipeline step.
        
        Args:
            value: Input value
            context: Connector context object
            
        Returns:
            Transformed value
        """
        self.ensure_one()
        
        if not self.function_id:
            return value
        
        parameters = self.get_parameters()
        return self.function_id.execute(value, context, parameters)
