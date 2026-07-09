# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import ValidationError
import json


class ConnectorSetting(models.Model):
    _name = 'connector.setting'
    _description = 'Connector Setting'
    _order = 'sequence, name'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, index=True)
    provider_id = fields.Many2one('connector.provider', string='Provider', ondelete='cascade', required=True)
    environment_id = fields.Many2one('connector.environment', string='Environment', ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    value = fields.Text(string='Value')
    value_type = fields.Selection([
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('password', 'Password'),
        ('json', 'JSON'),
    ], string='Value Type', default='string', required=True)
    
    encrypt = fields.Boolean(string='Encrypt', default=False, help='Encrypt the value when stored')
    required = fields.Boolean(string='Required', default=False)
    readonly = fields.Boolean(string='Readonly', default=False)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    _sql_constraints = [
        ('provider_env_code_unique', 
         'UNIQUE(provider_id, environment_id, code)', 
         'Setting code must be unique per provider and environment!'),
    ]
    
    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if record.code:
                if not record.code.replace('_', '').isalnum():
                    raise ValidationError(_('Setting code must contain only alphanumeric characters and underscores'))
                record.code = record.code.lower()
    
    def get_value(self):
        """
        Get the actual value based on value_type.
        
        Returns:
            Converted value or raw string
        """
        self.ensure_one()
        if not self.value:
            return None
        
        value = self.value
        
        # Decrypt if needed
        if self.encrypt:
            try:
                from cryptography.fernet import Fernet
                # This is a simplified implementation
                # In production, use proper key management
                key = self.env['ir.config_parameter'].sudo().get_param('connector.encryption_key')
                if key:
                    fernet = Fernet(key.encode())
                    value = fernet.decrypt(value.encode()).decode()
            except Exception:
                # If decryption fails, return raw value
                pass
        
        # Convert based on type
        if self.value_type == 'integer':
            try:
                return int(value)
            except ValueError:
                return 0
        elif self.value_type == 'float':
            try:
                return float(value)
            except ValueError:
                return 0.0
        elif self.value_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'json':
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {}
        
        return value
    
    def set_value(self, value):
        """
        Set the value with proper conversion and encryption.
        
        Args:
            value: Value to set
        """
        self.ensure_one()
        
        # Convert to string based on type
        if self.value_type == 'integer':
            value = str(int(value) if value is not None else 0)
        elif self.value_type == 'float':
            value = str(float(value) if value is not None else 0.0)
        elif self.value_type == 'boolean':
            value = str(bool(value))
        elif self.value_type == 'json':
            value = json.dumps(value if value is not None else {})
        else:
            value = str(value) if value is not None else ''
        
        # Encrypt if needed
        if self.encrypt:
            try:
                from cryptography.fernet import Fernet
                key = self.env['ir.config_parameter'].sudo().get_param('connector.encryption_key')
                if not key:
                    # Generate a new key if not exists
                    from cryptography.fernet import Fernet
                    key = Fernet.generate_key().decode()
                    self.env['ir.config_parameter'].sudo().set_param('connector.encryption_key', key)
                
                fernet = Fernet(key.encode())
                value = fernet.encrypt(value.encode()).decode()
            except Exception:
                # If encryption fails, store raw value
                pass
        
        self.value = value
    
    @api.model
    def get_provider_setting(self, provider_code, setting_code, environment_code=None, company_id=None):
        """
        Get setting value by provider code and setting code.
        
        Args:
            provider_code: Provider code
            setting_code: Setting code
            environment_code: Optional environment code
            company_id: Optional company ID
            
        Returns:
            Setting value or None
        """
        domain = [
            ('provider_id.code', '=', provider_code),
            ('code', '=', setting_code),
            ('active', '=', True),
        ]
        
        if environment_code:
            domain.append(('environment_id.code', '=', environment_code))
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        setting = self.search(domain, limit=1)
        if setting:
            return setting.get_value()
        return None
