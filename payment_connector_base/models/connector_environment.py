# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ConnectorEnvironment(models.Model):
    _name = 'connector.environment'
    _description = 'Connector Environment'
    _order = 'priority, name'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, index=True)
    provider_id = fields.Many2one('connector.provider', string='Provider', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    base_url = fields.Char(string='Base URL', help='Base URL for this environment')
    active = fields.Boolean(string='Active', default=True, required=True)
    priority = fields.Integer(string='Priority', default=10)
    
    # Relations
    setting_ids = fields.One2many('connector.setting', 'environment_id', string='Settings')
    endpoint_ids = fields.One2many('connector.endpoint', 'environment_id', string='Endpoints')
    
    _sql_constraints = [
        ('provider_company_code_unique', 
         'UNIQUE(provider_id, company_id, code)', 
         'Environment code must be unique per provider and company!'),
    ]
    
    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if record.code:
                if not record.code.replace('_', '').replace('-', '').isalnum():
                    raise ValidationError(_('Environment code must contain only alphanumeric characters, underscores, and hyphens'))
                record.code = record.code.lower()
    
    def get_setting(self, code):
        """
        Get setting value by code for this environment.
        
        Args:
            code: Setting code
            
        Returns:
            Setting value or None
        """
        setting = self.setting_ids.filtered(lambda s: s.code == code and s.active)
        if setting:
            return setting[0].get_value()
        return None
    
    def get_base_url(self):
        """
        Get base URL for this environment.
        
        Returns:
            Base URL string
        """
        return self.base_url or ''
