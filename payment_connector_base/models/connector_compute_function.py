# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import uuid
import base64
import hashlib
import json
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


class ConnectorComputeFunction(models.Model):
    _name = 'connector.compute.function'
    _description = 'Connector Compute Function'
    _order = 'category, name'
    
    name = fields.Char(string='Name', required=True, index=True)
    code = fields.Char(string='Code', required=True, index=True, copy=False)
    category = fields.Selection([
        ('string', 'String'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('json', 'JSON'),
        ('collection', 'Collection'),
        ('encoding', 'Encoding'),
        ('utility', 'Utility'),
        ('payment', 'Payment'),
        ('custom', 'Custom'),
    ], string='Category', required=True, default='utility')
    
    type = fields.Selection([
        ('builtin', 'Builtin'),
        ('custom', 'Custom'),
    ], string='Type', required=True, default='builtin')
    
    python_code = fields.Text(string='Python Code', help='Python code for custom functions')
    safe = fields.Boolean(string='Safe', default=True, help='Function is safe to execute')
    active = fields.Boolean(string='Active', default=True, required=True)
    description = fields.Text(string='Description')
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Function code must be unique!'),
    ]
    
    def execute(self, value, context=None, parameters=None):
        """
        Execute the compute function.
        
        Args:
            value: Input value
            context: Connector context object
            parameters: Additional parameters (dict)
            
        Returns:
            Transformed value
        """
        self.ensure_one()
        
        if self.type == 'builtin':
            return self._execute_builtin(value, context, parameters)
        elif self.type == 'custom':
            return self._execute_custom(value, context, parameters)
        
        return value
    
    def _execute_builtin(self, value, context=None, parameters=None):
        """
        Execute builtin function.
        
        Args:
            value: Input value
            context: Connector context object
            parameters: Additional parameters (dict)
            
        Returns:
            Transformed value
        """
        params = parameters or {}
        
        # String functions
        if self.code == 'upper':
            return str(value).upper()
        elif self.code == 'lower':
            return str(value).lower()
        elif self.code == 'trim':
            return str(value).strip()
        elif self.code == 'replace':
            old = params.get('old', '')
            new = params.get('new', '')
            return str(value).replace(old, new)
        elif self.code == 'split':
            delimiter = params.get('delimiter', ',')
            return str(value).split(delimiter)
        elif self.code == 'join':
            delimiter = params.get('delimiter', ',')
            if isinstance(value, list):
                return delimiter.join(str(v) for v in value)
            return str(value)
        elif self.code == 'substring':
            start = params.get('start', 0)
            length = params.get('length', 0)
            return str(value)[start:start+length]
        elif self.code == 'length':
            return len(str(value))
        elif self.code == 'pad_left':
            char = params.get('char', ' ')
            length = params.get('length', 0)
            return str(value).rjust(length, char)
        elif self.code == 'pad_right':
            char = params.get('char', ' ')
            length = params.get('length', 0)
            return str(value).ljust(length, char)
        
        # Number functions
        elif self.code == 'round':
            digits = params.get('digits', 2)
            try:
                return float(Decimal(str(value)).quantize(Decimal('1e-{}'.format(digits)), rounding=ROUND_HALF_UP))
            except (ValueError, InvalidOperation):
                return round(float(value), digits)
        elif self.code == 'ceil':
            return int(float(value)) + (1 if float(value) > int(float(value)) else 0)
        elif self.code == 'floor':
            return int(float(value))
        elif self.code == 'abs':
            return abs(float(value))
        elif self.code == 'multiply':
            factor = params.get('factor', 1)
            return float(value) * float(factor)
        elif self.code == 'divide':
            divisor = params.get('divisor', 1)
            if divisor == 0:
                return 0
            return float(value) / float(divisor)
        elif self.code == 'plus':
            addend = params.get('addend', 0)
            return float(value) + float(addend)
        elif self.code == 'minus':
            subtrahend = params.get('subtrahend', 0)
            return float(value) - float(subtrahend)
        elif self.code == 'mod':
            divisor = params.get('divisor', 1)
            if divisor == 0:
                return 0
            return float(value) % float(divisor)
        
        # Date functions
        elif self.code == 'today':
            return fields.Date.today()
        elif self.code == 'now':
            return fields.Datetime.now()
        elif self.code == 'format_date':
            fmt = params.get('format', '%Y-%m-%d')
            if isinstance(value, (date, datetime)):
                return value.strftime(fmt)
            return str(value)
        elif self.code == 'timestamp':
            if isinstance(value, (date, datetime)):
                return int(value.timestamp())
            return 0
        elif self.code == 'add_day':
            days = params.get('days', 0)
            if isinstance(value, date):
                return value + timedelta(days=days)
            return value
        elif self.code == 'add_month':
            months = params.get('months', 0)
            if isinstance(value, date):
                year = value.year + (value.month + months - 1) // 12
                month = (value.month + months - 1) % 12 + 1
                day = min(value.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
                return value.replace(year=year, month=month, day=day)
            return value
        
        # JSON functions
        elif self.code == 'json_encode':
            return json.dumps(value)
        elif self.code == 'json_decode':
            if isinstance(value, str):
                return json.loads(value)
            return value
        elif self.code == 'merge':
            other = params.get('other', {})
            if isinstance(value, dict) and isinstance(other, dict):
                return {**value, **other}
            return value
        elif self.code == 'flatten':
            if isinstance(value, dict):
                result = {}
                for k, v in value.items():
                    if isinstance(v, dict):
                        result.update(self._flatten_dict(v, k))
                    else:
                        result[k] = v
                return result
            return value
        
        # Collection functions
        elif self.code == 'sum':
            if isinstance(value, list):
                return sum(float(v) for v in value if isinstance(v, (int, float)))
            return float(value)
        elif self.code == 'max':
            if isinstance(value, list):
                return max(value) if value else None
            return value
        elif self.code == 'min':
            if isinstance(value, list):
                return min(value) if value else None
            return value
        elif self.code == 'first':
            if isinstance(value, list):
                return value[0] if value else None
            return value
        elif self.code == 'last':
            if isinstance(value, list):
                return value[-1] if value else None
            return value
        elif self.code == 'count':
            if isinstance(value, (list, dict)):
                return len(value)
            return 1 if value else 0
        
        # Encoding functions
        elif self.code == 'base64':
            if isinstance(value, str):
                return base64.b64encode(value.encode()).decode()
            return value
        elif self.code == 'base64_decode':
            if isinstance(value, str):
                return base64.b64decode(value.encode()).decode()
            return value
        elif self.code == 'md5':
            if isinstance(value, str):
                return hashlib.md5(value.encode()).hexdigest()
            return value
        elif self.code == 'sha256':
            if isinstance(value, str):
                return hashlib.sha256(value.encode()).hexdigest()
            return value
        elif self.code == 'url_encode':
            from urllib.parse import quote
            return quote(str(value))
        elif self.code == 'url_decode':
            from urllib.parse import unquote
            return unquote(str(value))
        
        # Utility functions
        elif self.code == 'uuid':
            return str(uuid.uuid4())
        elif self.code == 'random':
            import random
            return random.random()
        elif self.code == 'coalesce':
            alternatives = params.get('alternatives', [])
            if value is not None:
                return value
            for alt in alternatives:
                if alt is not None:
                    return alt
            return None
        elif self.code == 'default':
            default = params.get('default', None)
            return value if value is not None else default
        elif self.code == 'bool':
            return bool(value)
        
        # Payment functions
        elif self.code == 'format_money':
            locale = params.get('locale', 'en_US')
            # Simplified implementation
            return str(float(value))
        elif self.code == 'bank_amount':
            # Remove decimal separator for banking systems
            return str(int(float(value) * 100))
        elif self.code == 'remove_dot':
            return str(value).replace('.', '')
        elif self.code == 'remove_comma':
            return str(value).replace(',', '')
        
        return value
    
    def _execute_custom(self, value, context=None, parameters=None):
        """
        Execute custom Python function.
        
        Args:
            value: Input value
            context: Connector context object
            parameters: Additional parameters (dict)
            
        Returns:
            Transformed value
        """
        if not self.python_code:
            return value
        
        try:
            local_dict = {
                'value': value,
                'context': context,
                'parameters': parameters or {},
                'env': self.env,
            }
            exec(self.python_code, {'__builtins__': {}}, local_dict)
            return local_dict.get('result', value)
        except Exception:
            return value
    
    def _flatten_dict(self, d, parent_key=''):
        """
        Helper function to flatten nested dictionaries.
        
        Args:
            d: Dictionary to flatten
            parent_key: Parent key prefix
            
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)
