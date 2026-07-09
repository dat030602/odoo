# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import hashlib
import hmac
import json


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
        
        # Convert data to string if it's a dict
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True)
        
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
    
    def _hash_md5(self, data):
        """
        MD5 hash.
        
        Args:
            data: Data to hash
            
        Returns:
            MD5 hash string
        """
        return hashlib.md5(data.encode()).hexdigest()
    
    def _hash_sha1(self, data):
        """
        SHA1 hash.
        
        Args:
            data: Data to hash
            
        Returns:
            SHA1 hash string
        """
        return hashlib.sha1(data.encode()).hexdigest()
    
    def _hash_sha256(self, data):
        """
        SHA256 hash.
        
        Args:
            data: Data to hash
            
        Returns:
            SHA256 hash string
        """
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _hash_sha512(self, data):
        """
        SHA512 hash.
        
        Args:
            data: Data to hash
            
        Returns:
            SHA512 hash string
        """
        return hashlib.sha512(data.encode()).hexdigest()
    
    def _hash_hmac_sha256(self, data, secret):
        """
        HMAC SHA256 hash.
        
        Args:
            data: Data to hash
            secret: Secret key
            
        Returns:
            HMAC SHA256 hash string
        """
        if not secret:
            return ''
        
        return hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _hash_hmac_sha512(self, data, secret):
        """
        HMAC SHA512 hash.
        
        Args:
            data: Data to hash
            secret: Secret key
            
        Returns:
            HMAC SHA512 hash string
        """
        if not secret:
            return ''
        
        return hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha512
        ).hexdigest()
    
    def _hash_custom(self, data, secret, context):
        """
        Custom hash using Python class.
        
        Args:
            data: Data to hash
            secret: Secret key
            context: Connector context object
            
        Returns:
            Hash string
        """
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
        """
        Build signature string from dictionary.
        
        Args:
            data: Dictionary of parameters
            separator: Separator between parameters
            sort: Sort keys alphabetically
            
        Returns:
            Signature string
        """
        if not isinstance(data, dict):
            return str(data)
        
        if sort:
            keys = sorted(data.keys())
        else:
            keys = data.keys()
        
        parts = []
        for key in keys:
            value = data[key]
            if value is not None:
                parts.append(f"{key}={value}")
        
        return separator.join(parts)
