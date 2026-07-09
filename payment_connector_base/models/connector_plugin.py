# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ConnectorPlugin(models.Model):
    _name = 'connector.plugin'
    _description = 'Connector Plugin'
    _order = 'sequence, name'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, index=True, copy=False)
    provider_id = fields.Many2one('connector.provider', string='Provider', ondelete='cascade')
    module_name = fields.Char(string='Module Name', help='Module that provides this plugin')
    python_class = fields.Char(string='Python Class', help='Full Python class path (e.g., my_module.MyPlugin)')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True, required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Plugin code must be unique!'),
    ]
    
    def get_plugin_instance(self):
        """
        Get the plugin instance.
        
        Returns:
            Plugin instance or None
        """
        self.ensure_one()
        if not self.python_class:
            return None
        
        try:
            module_path, class_name = self.python_class.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            plugin_class = getattr(module, class_name)
            return plugin_class()
        except Exception:
            return None
