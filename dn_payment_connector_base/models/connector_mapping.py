# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ConnectorMapping(models.Model):
    _name = 'connector.mapping'
    _description = 'Connector Mapping'
    _order = 'sequence, name'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, index=True, copy=False)
    api_id = fields.Many2one('connector.api', string='API', required=True, ondelete='cascade')
    provider_id = fields.Many2one(related='api_id.provider_id', string='Provider', store=True, readonly=True)
    
    type = fields.Selection([
        ('HEADER', 'Header'),
        ('QUERY', 'Query Parameter'),
        ('PATH', 'Path Parameter'),
        ('PAYLOAD', 'Payload'),
        ('RESPONSE', 'Response'),
    ], string='Mapping Type', required=True)
    
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True, required=True)
    description = fields.Text(string='Description')
    
    # Relations
    line_ids = fields.One2many('connector.mapping.line', 'mapping_id', string='Mapping Lines')
    
    # Computed fields for stat buttons
    line_count = fields.Integer(string='Line Count', compute='_compute_line_count')
    
    @api.depends('line_ids')
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)
    
    def action_view_lines(self):
        """
        Action to view mapping lines.
        """
        self.ensure_one()
        return {
            'name': _('Mapping Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'connector.mapping.line',
            'view_mode': 'tree,form',
            'domain': [('mapping_id', '=', self.id)],
            'context': {'default_mapping_id': self.id}
        }
    
    _sql_constraints = [
        ('api_type_unique', 
         'UNIQUE(api_id, type)', 
         'Mapping type must be unique per API!'),
    ]
    
    def build_dict(self, context=None):
        """
        Build dictionary from mapping lines.
        
        Args:
            context: Connector context object
            
        Returns:
            Dictionary of mapped values
        """
        self.ensure_one()
        result = {}
        
        for line in self.line_ids.filtered(lambda l: l.active):
            value = line.get_value(context)
            if value is not None or not line.ignore_if_empty:
                result[line.key] = value
        
        return result
    
    def preview_mapping(self, source_record):
        """
        Preview mapping for a source record.
        
        Args:
            source_record: Source Odoo record
            
        Returns:
            Dictionary of mapped values with debug info
        """
        self.ensure_one()
        # This will be implemented by the mapping engine
        return {}
