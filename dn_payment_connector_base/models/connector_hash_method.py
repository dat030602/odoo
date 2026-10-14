# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import hashlib
import hmac
import json
import urllib.parse


class ConnectorHashMethod(models.Model):
    _name = 'connector.hash.method'
    _description = 'Connector Hash Method'
    _order = 'name'
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, index=True, copy=False)
    algorithm = fields.Selection([
        ('md5', 'MD5'),
        ('sha1', 'SHA1'),
        ('sha256', 'SHA256'),
        ('sha512', 'SHA512'),
        ('hmac_sha256', 'HMAC SHA256'),
        ('hmac_sha512', 'HMAC SHA512'),
        ('custom', 'Custom'),
    ], string='Algorithm', required=True)
    
    hash_style = fields.Selection([
        ('sorted_query', 'Sorted Query String'),
        ('pipe_separated', 'Pipe Separated'),
        ('json_body', 'JSON Body'),
        ('custom', 'Custom'),
    ], string='Hash Style', default='sorted_query')
    
    pipe_fields = fields.Text(
        string='Pipe Fields',
        help='Ordered list of field names for pipe-separated hash (one per line)'
    )
    
    exclude_keys = fields.Text(
        string='Exclude Keys',
        help='Keys to exclude from hash computation (one per line, e.g. vnp_SecureHash)'
    )
    
    python_class = fields.Char(string='Python Class', help='Custom Python class for hash')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True, required=True)
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Hash method code must be unique!'),
    ]
    
    def hash(self, data, secret=None, context=None):
        """
        Generate hash from data.
        
        Args:
            data: Data to hash (string or dict)
            secret: Secret key for HMAC
            context: Connector context object
            
        Returns:
            Hash string
        """
        self.ensure_one()
        
        if isinstance(data, dict):
            return self.build_signature(data, secret)
        
        if self.algorithm == 'md5':
            return self._hash_md5(data)
        elif self.algorithm == 'sha1':
            return self._hash_sha1(data)
        elif self.algorithm == 'sha256':
            return self._hash_sha256(data)
        elif self.algorithm == 'sha512':
            return self._hash_sha512(data)
        elif self.algorithm == 'hmac_sha256':
            return self._hash_hmac_sha256(data, secret)
        elif self.algorithm == 'hmac_sha512':
            return self._hash_hmac_sha512(data, secret)
        elif self.algorithm == 'custom':
            return self._hash_custom(data, secret, context)
        
        return ''
    
    def build_signature(self, params, secret, style=None):
        """
        Generic: Build signature from params using this method's algorithm.
        Dispatches to sorted_query, pipe_separated, or json_body based on hash_style.
        """
        self.ensure_one()
        style = style or self.hash_style or 'sorted_query'
        engine = self.env['connector.hash.engine']
        
        exclude = []
        if self.exclude_keys:
            exclude = [k.strip() for k in self.exclude_keys.split('\n') if k.strip()]
        
        if style == 'sorted_query':
            return engine.build_sorted_query_hash(
                params, secret, algorithm=self.algorithm, exclude_keys=exclude
            )
        elif style == 'pipe_separated':
            pipe_fields_list = []
            if self.pipe_fields:
                pipe_fields_list = [f.strip() for f in self.pipe_fields.split('\n') if f.strip()]
            return engine.build_pipe_separated_hash(
                pipe_fields_list, params, secret, algorithm=self.algorithm
            )
        elif style == 'json_body':
            data_str = json.dumps(params, sort_keys=True)
            return self.hash(data_str, secret=secret)
        elif style == 'custom':
            return self._hash_custom(params, secret, None)
        
        return ''

    def verify_signature(self, params, received_hash, secret, style=None):
        """
        Generic: Verify a received hash against computed hash.
        """
        self.ensure_one()
        style = style or self.hash_style or 'sorted_query'
        engine = self.env['connector.hash.engine']
        
        exclude = []
        if self.exclude_keys:
            exclude = [k.strip() for k in self.exclude_keys.split('\n') if k.strip()]
        pipe_fields_list = []
        if self.pipe_fields:
            pipe_fields_list = [f.strip() for f in self.pipe_fields.split('\n') if f.strip()]
            
        return engine.verify_hash(
            received_hash=received_hash,
            params=params,
            secret=secret,
            algorithm=self.algorithm,
            hash_style=style,
            exclude_keys=exclude,
            pipe_fields=pipe_fields_list,
        )

    def _hash_md5(self, data):
        return hashlib.md5(str(data).encode()).hexdigest()
    
    def _hash_sha1(self, data):
        return hashlib.sha1(str(data).encode()).hexdigest()
    
    def _hash_sha256(self, data):
        return hashlib.sha256(str(data).encode()).hexdigest()
    
    def _hash_sha512(self, data):
        return hashlib.sha512(str(data).encode()).hexdigest()
    
    def _hash_hmac_sha256(self, data, secret):
        if not secret:
            return ''
        return hmac.new(str(secret).encode(), str(data).encode(), hashlib.sha256).hexdigest()
    
    def _hash_hmac_sha512(self, data, secret):
        if not secret:
            return ''
        return hmac.new(str(secret).encode(), str(data).encode(), hashlib.sha512).hexdigest()
    
    def _hash_custom(self, data, secret, context):
        if not self.python_class:
            return ''
        try:
            module_path, class_name = self.python_class.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            hash_class = getattr(module, class_name)
            hash_instance = hash_class()
            return hash_instance.hash(data, secret, context)
        except Exception:
            return ''
    
    def build_signature_string(self, data, separator='&', sort=True):
        if not isinstance(data, dict):
            return str(data)
        keys = sorted(data.keys()) if sort else data.keys()
        parts = []
        for key in keys:
            value = data[key]
            if value is not None:
                parts.append(f"{key}={value}")
        return separator.join(parts)
