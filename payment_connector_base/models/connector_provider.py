# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ConnectorProvider(models.Model):
    _name = 'connector.provider'
    _description = 'Connector Provider'
    _order = 'sequence, name'
    
    name = fields.Char(string='Display Name', required=True, index=True)
    code = fields.Char(string='Code', required=True, index=True, copy=False)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True, required=True)
    module_name = fields.Char(string='Module Name', help='Module that provides this provider')
    company_dependent = fields.Boolean(string='Company Dependent', default=False)
    icon = fields.Binary(string='Icon')
    sequence = fields.Integer(string='Sequence', default=10)
    version = fields.Char(string='Version')
    author = fields.Char(string='Author')
    
    # Relations
    environment_ids = fields.One2many('connector.environment', 'provider_id', string='Environments')
    api_ids = fields.One2many('connector.api', 'provider_id', string='APIs')
    setting_ids = fields.One2many('connector.setting', 'provider_id', string='Settings')
    plugin_ids = fields.One2many('connector.plugin', 'provider_id', string='Plugins')
    
    # Computed fields for stat buttons
    environment_count = fields.Integer(string='Environment Count', compute='_compute_counts')
    api_count = fields.Integer(string='API Count', compute='_compute_counts')
    
    @api.depends('environment_ids', 'api_ids')
    def _compute_counts(self):
        for record in self:
            record.environment_count = len(record.environment_ids)
            record.api_count = len(record.api_ids)
    
    def action_view_environments(self):
        """
        Action to view environments.
        """
        self.ensure_one()
        return {
            'name': _('Environments'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.environment',
            'view_mode': 'tree,form',
            'domain': [('provider_id', '=', self.id)],
            'context': {'default_provider_id': self.id}
        }
    
    def action_view_apis(self):
        """
        Action to view APIs.
        """
        self.ensure_one()
        return {
            'name': _('APIs'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.api',
            'view_mode': 'tree,form',
            'domain': [('provider_id', '=', self.id)],
            'context': {'default_provider_id': self.id}
        }
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Provider code must be unique!'),
    ]
    
    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if record.code:
                # Ensure code is lowercase and contains only alphanumeric characters and underscores
                if not record.code.replace('_', '').isalnum():
                    raise ValidationError(_('Provider code must contain only alphanumeric characters and underscores'))
                record.code = record.code.lower()
    
    def get_setting(self, code, environment_id=None, company_id=None):
        """
        Get setting value by code for this provider.
        
        Args:
            code: Setting code
            environment_id: Optional environment ID
            company_id: Optional company ID for multi-company support
            
        Returns:
            Setting value or None
        """
        domain = [
            ('provider_id', '=', self.id),
            ('code', '=', code),
            ('active', '=', True),
        ]
        
        if environment_id:
            domain.append(('environment_id', '=', environment_id))
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        setting = self.env['connector.setting'].search(domain, limit=1)
        if setting:
            return setting.get_value()
        return None
    
    def get_environment(self, code=None, company_id=None):
        """
        Get environment by code for this provider.
        
        Args:
            code: Environment code (optional)
            company_id: Company ID for multi-company support
            
        Returns:
            Environment record or None
        """
        domain = [('provider_id', '=', self.id), ('active', '=', True)]
        
        if code:
            domain.append(('code', '=', code))
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        return self.env['connector.environment'].search(domain, limit=1)
