# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json


class ConnectorMappingLine(models.Model):
    _name = 'connector.mapping.line'
    _description = 'Connector Mapping Line'
    _order = 'mapping_id, sequence, id'
    
    mapping_id = fields.Many2one('connector.mapping', string='Mapping', required=True, ondelete='cascade')
    parent_id = fields.Many2one('connector.mapping.line', string='Parent Line', ondelete='cascade')
    child_ids = fields.One2many('connector.mapping.line', 'parent_id', string='Child Lines')
    
    sequence = fields.Integer(string='Sequence', default=10)
    key = fields.Char(string='Key', required=True, help='Target key name')
    display_name = fields.Char(string='Display Name', help='Human-readable name for UI')
    
    # Source Configuration
    source_type = fields.Selection([
        ('FIELD', 'Field'),
        ('SETTING', 'Setting'),
        ('FIXED', 'Fixed Value'),
        ('VARIABLE', 'Variable'),
        ('CONTEXT', 'Context'),
        ('PLUGIN', 'Plugin'),
        ('EXPRESSION', 'Expression'),
        ('NONE', 'None'),
    ], string='Source Type', required=True, default='FIELD')
    
    source_path = fields.Char(string='Source Path', help='Path to source value (e.g., partner_id.name)')
    fixed_value = fields.Text(string='Fixed Value')
    default_value = fields.Text(string='Default Value')
    
    # Compute Pipeline
    compute_pipeline_ids = fields.One2many('connector.compute.pipeline', 'mapping_line_id', string='Compute Pipeline')
    
    # Conditions
    condition = fields.Char(string='Condition', help='Python expression for conditional mapping')
    
    # Validation
    required = fields.Boolean(string='Required', default=False, help='Value must not be None')
    ignore_if_empty = fields.Boolean(string='Ignore if Empty', default=False, help='Don\'t include in output if value is empty')
    
    # Data Type
    datatype = fields.Selection([
        ('STRING', 'String'),
        ('INTEGER', 'Integer'),
        ('FLOAT', 'Float'),
        ('BOOLEAN', 'Boolean'),
        ('DATE', 'Date'),
        ('DATETIME', 'Datetime'),
        ('OBJECT', 'Object'),
        ('ARRAY', 'Array'),
        ('NULL', 'Null'),
    ], string='Data Type', required=True, default='STRING')
    
    # Array/Loop Configuration
    is_array = fields.Boolean(string='Is Array', default=False, help='This field represents an array')
    loop_source = fields.Char(string='Loop Source', help='Source path for loop iteration (e.g., invoice_line_ids)')
    loop_alias = fields.Char(string='Loop Alias', default='item', help='Alias for loop variable')
    
    description = fields.Text(string='Description')
    
    def get_value(self, context=None):
        """
        Get the mapped value for this line.
        
        Args:
            context: Connector context object containing source data, variables, etc.
            
        Returns:
            Mapped value
        """
        self.ensure_one()
        
        # Step 1: Resolve Source
        value = self._resolve_source(context)
        
        # Step 2: Apply Default
        if value is None and self.default_value:
            value = self.default_value
        
        # Step 3: Required Validation
        if self.required and value is None:
            raise ValidationError(_('Required field %s is empty') % self.key)
        
        # Step 4: Condition Check
        if self.condition and context:
            if not self._check_condition(context):
                return None
        
        # Step 5: Compute Pipeline
        if self.compute_pipeline_ids and value is not None:
            value = self._execute_compute_pipeline(value, context)
        
        # Step 6: Data Type Conversion
        if value is not None:
            value = self._convert_datatype(value)
        
        # Step 7: Variable Save (if configured)
        # This will be implemented by the variable engine
        
        return value
    
    def _resolve_source(self, context):
        """
        Resolve value from source.
        
        Args:
            context: Connector context object
            
        Returns:
            Resolved value
        """
        if not context:
            return None
        
        if self.source_type == 'FIELD':
            return self._resolve_field(context)
        elif self.source_type == 'SETTING':
            return self._resolve_setting(context)
        elif self.source_type == 'FIXED':
            return self.fixed_value
        elif self.source_type == 'VARIABLE':
            return self._resolve_variable(context)
        elif self.source_type == 'CONTEXT':
            return self._resolve_context(context)
        elif self.source_type == 'PLUGIN':
            return self._resolve_plugin(context)
        elif self.source_type == 'EXPRESSION':
            return self._resolve_expression(context)
        
        return None
    
    def _resolve_field(self, context):
        """
        Resolve value from field path.
        
        Args:
            context: Connector context object
            
        Returns:
            Field value
        """
        if not self.source_path or not hasattr(context, 'record'):
            return None
        
        record = context.record
        path_parts = self.source_path.split('.')
        
        try:
            value = record
            for part in path_parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                    if callable(value):
                        value = value()
                else:
                    return None
            return value
        except Exception:
            return None
    
    def _resolve_setting(self, context):
        """
        Resolve value from setting.
        
        Args:
            context: Connector context object
            
        Returns:
            Setting value
        """
        if not self.source_path or not hasattr(context, 'provider'):
            return None
        
        return context.provider.get_setting(self.source_path)
    
    def _resolve_variable(self, context):
        """
        Resolve value from runtime variable.
        
        Args:
            context: Connector context object
            
        Returns:
            Variable value
        """
        if not self.source_path or not hasattr(context, 'variables'):
            return None
        
        return context.variables.get(self.source_path)
    
    def _resolve_context(self, context):
        """
        Resolve value from context (built-in variables).
        
        Args:
            context: Connector context object
            
        Returns:
            Context value
        """
        if not self.source_path:
            return None
        
        # Built-in context variables
        context_vars = {
            'today': fields.Date.today(),
            'now': fields.Datetime.now(),
            'user': self.env.user,
            'company': self.env.company,
            'lang': self.env.context.get('lang'),
            'tz': self.env.context.get('tz'),
        }
        
        return context_vars.get(self.source_path)
    
    def _resolve_plugin(self, context):
        """
        Resolve value from plugin.
        
        Args:
            context: Connector context object
            
        Returns:
            Plugin return value
        """
        if not self.source_path:
            return None
        
        # This will be implemented by the plugin engine
        return None
    
    def _resolve_expression(self, context):
        """
        Resolve value from Python expression.
        
        Args:
            context: Connector context object
            
        Returns:
            Expression result
        """
        if not self.source_path:
            return None
        
        try:
            # Safe evaluation of expression
            # This is a simplified implementation
            # In production, use proper safe_eval with restricted globals
            local_dict = {
                'record': getattr(context, 'record', None),
                'env': self.env,
                'today': fields.Date.today(),
                'now': fields.Datetime.now(),
            }
            return eval(self.source_path, {'__builtins__': {}}, local_dict)
        except Exception:
            return None
    
    def _check_condition(self, context):
        """
        Check if condition is met.
        
        Args:
            context: Connector context object
            
        Returns:
            Boolean
        """
        if not self.condition:
            return True
        
        try:
            local_dict = {
                'record': getattr(context, 'record', None),
                'env': self.env,
            }
            return bool(eval(self.condition, {'__builtins__': {}}, local_dict))
        except Exception:
            return False
    
    def _execute_compute_pipeline(self, value, context):
        """
        Execute compute pipeline on value.
        
        Args:
            value: Input value
            context: Connector context object
            
        Returns:
            Transformed value
        """
        for pipeline_step in self.compute_pipeline_ids.sorted('sequence'):
            value = pipeline_step.execute(value, context)
            if value is None and pipeline_step.stop_if_none:
                break
        return value
    
    def _convert_datatype(self, value):
        """
        Convert value to specified datatype.
        
        Args:
            value: Input value
            
        Returns:
            Converted value
        """
        if value is None:
            return None
        
        try:
            if self.datatype == 'INTEGER':
                return int(float(value))
            elif self.datatype == 'FLOAT':
                return float(value)
            elif self.datatype == 'BOOLEAN':
                return bool(value)
            elif self.datatype == 'STRING':
                return str(value)
            elif self.datatype == 'DATE':
                if isinstance(value, str):
                    return fields.Date.from_string(value)
                return value
            elif self.datatype == 'DATETIME':
                if isinstance(value, str):
                    return fields.Datetime.from_string(value)
                return value
            elif self.datatype == 'OBJECT':
                if isinstance(value, str):
                    return json.loads(value)
                return value
            elif self.datatype == 'ARRAY':
                if isinstance(value, str):
                    return json.loads(value)
                if not isinstance(value, list):
                    return [value]
                return value
            elif self.datatype == 'NULL':
                return None
        except Exception:
            pass
        
        return value
