# -*- coding: utf-8 -*-

from odoo import models, api, _


class ComputeEngine(models.AbstractModel):
    _name = 'connector.compute.engine'
    _description = 'Connector Compute Engine'
    
    @api.model
    def execute_pipeline(self, value, pipeline_steps, context):
        """
        Execute compute pipeline in sequence.
        """
        if not pipeline_steps or value is None:
            return value
            
        for step in pipeline_steps:
            value = step.execute(value, context)
            if value is None and getattr(step, 'stop_if_none', False):
                break
        return value
