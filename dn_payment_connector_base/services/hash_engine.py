# -*- coding: utf-8 -*-

from odoo import models, api, _
import hashlib
import hmac
import urllib.parse
import json


class HashEngine(models.AbstractModel):
    _name = 'connector.hash.engine'
    _description = 'Connector Hash Engine'
    
    @api.model
    def generate_hash(self, context):
        """
        Use endpoint's hash_method_id to generate hash from context data.
        """
        endpoint = getattr(context, 'endpoint', None)
        if not endpoint or not endpoint.hash_method_id:
            return ''
        
        provider = context.provider
        environment = context.environment
        secret_setting_code = endpoint.secret_setting_code or 'hash_secret'
        secret = provider.get_setting(secret_setting_code, environment.id if environment else None)
        
        data = context.get_variable('hash_data')
        if data is None:
            # Fall back to query or payload
            data = context.get_variable('query_params') or context.get_variable('payload')
            
        return endpoint.hash_method_id.build_signature(data, secret)
    
    @api.model
    def build_sorted_query_hash(self, params, secret, algorithm='hmac_sha512', exclude_keys=None):
        """
        Generic: Build hash from sorted URL-encoded query parameters.
        Compatible with standard payment gateways (VNPay, MoMo, etc.).
        
        1. Sort params alphabetically by key.
        2. URL-encode keys and values using urllib.parse.quote_plus (PHP urlencode compatible).
        3. Join with '&'.
        4. Hash with algorithm / HMAC.
        """
        if not params or not secret:
            return ''
            
        exclude = set(exclude_keys or ['vnp_SecureHash', 'vnp_SecureHashType'])
        
        sorted_keys = sorted(params.keys())
        query_parts = []
        for key in sorted_keys:
            if key in exclude:
                continue
            val = params.get(key)
            if val is not None and str(val) != '':
                encoded_key = urllib.parse.quote_plus(str(key))
                encoded_val = urllib.parse.quote_plus(str(val))
                query_parts.append(f"{encoded_key}={encoded_val}")
                
        hash_data = '&'.join(query_parts)
        return self._compute_digest(hash_data, secret, algorithm)

    @api.model
    def build_pipe_separated_hash(self, fields_list, values_dict, secret, algorithm='hmac_sha512'):
        """
        Generic: Build hash from pipe-separated field concatenation.
        Used by VNPay querydr/refund, bank reconciliation APIs, etc.
        """
        if not fields_list or not secret:
            return ''
            
        parts = []
        for field in fields_list:
            val = values_dict.get(field, '')
            parts.append(str(val) if val is not None else '')
            
        pipe_string = '|'.join(parts)
        return self._compute_digest(pipe_string, secret, algorithm)

    @api.model
    def verify_hash(self, received_hash, params, secret, algorithm='hmac_sha512',
                    hash_style='sorted_query', exclude_keys=None, pipe_fields=None):
        """
        Generic: Verify a received hash against computed hash.
        """
        if not received_hash or not secret or not params:
            return False
            
        if hash_style == 'sorted_query':
            expected_hash = self.build_sorted_query_hash(
                params, secret, algorithm=algorithm, exclude_keys=exclude_keys
            )
        elif hash_style == 'pipe_separated':
            expected_hash = self.build_pipe_separated_hash(
                pipe_fields or [], params, secret, algorithm=algorithm
            )
        else:
            return False
            
        return hmac.compare_digest(str(received_hash).lower(), str(expected_hash).lower())

    def _compute_digest(self, data, secret, algorithm):
        data_bytes = data.encode('utf-8')
        secret_bytes = str(secret).encode('utf-8')
        
        if algorithm == 'hmac_sha512':
            return hmac.new(secret_bytes, data_bytes, hashlib.sha512).hexdigest()
        elif algorithm == 'hmac_sha256':
            return hmac.new(secret_bytes, data_bytes, hashlib.sha256).hexdigest()
        elif algorithm == 'sha512':
            return hashlib.sha512(data_bytes).hexdigest()
        elif algorithm == 'sha256':
            return hashlib.sha256(data_bytes).hexdigest()
        elif algorithm == 'md5':
            return hashlib.md5(data_bytes).hexdigest()
        return ''
