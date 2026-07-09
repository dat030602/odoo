# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import ValidationError


class ConnectorAPI(models.Model):
    _name = 'connector.api'
    _description = 'Connector API'
    _order = 'sequence, name'
    
    name = fields.Char(string='Name', required=True, index=True)
    code = fields.Char(string='Code', required=True, index=True, copy=False)
    provider_id = fields.Many2one('connector.provider', string='Provider', required=True, ondelete='cascade')
    version = fields.Char(string='Version', default='1.0')
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True, required=True)
    
    # Relations
    endpoint_ids = fields.One2many('connector.endpoint', 'api_id', string='Endpoints')
    mapping_ids = fields.One2many('connector.mapping', 'api_id', string='Mappings')
    
    # Computed fields for stat buttons
    endpoint_count = fields.Integer(string='Endpoint Count', compute='_compute_counts')
    mapping_count = fields.Integer(string='Mapping Count', compute='_compute_counts')
    
    @api.depends('endpoint_ids', 'mapping_ids')
    def _compute_counts(self):
        for record in self:
            record.endpoint_count = len(record.endpoint_ids)
            record.mapping_count = len(record.mapping_ids)
    
    def action_view_endpoints(self):
        """
        Action to view endpoints.
        """
        self.ensure_one()
        return {
            'name': _('Endpoints'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.endpoint',
            'view_mode': 'tree,form',
            'domain': [('api_id', '=', self.id)],
            'context': {'default_api_id': self.id}
        }
    
    def action_view_mappings(self):
        """
        Action to view mappings.
        """
        self.ensure_one()
        return {
            'name': _('Mappings'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.mapping',
            'view_mode': 'tree,form',
            'domain': [('api_id', '=', self.id)],
            'context': {'default_api_id': self.id}
        }
    
    _sql_constraints = [
        ('provider_code_unique', 
         'UNIQUE(provider_id, code)', 
         'API code must be unique per provider!'),
    ]
    
    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if record.code:
                if not record.code.replace('_', '').isalnum():
                    raise ValidationError(_('API code must contain only alphanumeric characters and underscores'))
                record.code = record.code.lower()
    
    def get_endpoint(self, environment_id=None, company_id=None):
        """
        Get endpoint for this API based on environment and company.
        
        Args:
            environment_id: Optional environment ID
            company_id: Optional company ID
            
        Returns:
            Endpoint record or None
        """
        domain = [('api_id', '=', self.id), ('active', '=', True)]
        
        if environment_id:
            domain.append(('environment_id', '=', environment_id))
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        return self.env['connector.endpoint'].search(domain, limit=1)
    
    def get_mapping(self, mapping_type):
        """
        Get mapping by type for this API.
        
        Args:
            mapping_type: Mapping type (HEADER, QUERY, PATH, PAYLOAD, RESPONSE)
            
        Returns:
            Mapping record or None
        """
        return self.mapping_ids.filtered(lambda m: m.type == mapping_type and m.active)
