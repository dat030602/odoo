# -*- coding: utf-8 -*-

from odoo import models, api, _
import requests
import time
import urllib.parse
import json


class HTTPEngine(models.AbstractModel):
    _name = 'connector.http.engine'
    _description = 'Connector HTTP Engine'
    
    @api.model
    def send_request(self, context):
        """
        Send HTTP request based on endpoint configuration.
        """
        endpoint = context.endpoint
        url = endpoint.get_full_url()
        method = endpoint.method.upper()
        
        headers = context.get_variable('headers') or {}
        query_params = context.get_variable('query_params') or {}
        payload = context.get_variable('payload')
        
        timeout = endpoint.timeout or 30
        retry_count = endpoint.retry or 1
        
        req_kwargs = {
            'headers': headers,
            'params': query_params if query_params else None,
            'timeout': timeout,
        }
        
        if endpoint.body_type == 'JSON' and payload is not None:
            req_kwargs['json'] = payload
        elif endpoint.body_type in ('FORM', 'MULTIPART') and payload is not None:
            req_kwargs['data'] = payload
        elif endpoint.body_type == 'RAW' and payload is not None:
            req_kwargs['data'] = payload if isinstance(payload, bytes) else str(payload).encode()
            
        start_time = time.time()
        last_error = None
        
        for attempt in range(max(1, retry_count)):
            try:
                resp = requests.request(method, url, **req_kwargs)
                duration = time.time() - start_time
                
                return {
                    'success': 200 <= resp.status_code < 300,
                    'status_code': resp.status_code,
                    'response_body': resp.text,
                    'response_headers': dict(resp.headers),
                    'duration': duration,
                }
            except Exception as e:
                last_error = str(e)
                if attempt < retry_count - 1:
                    time.sleep(1)
                    
        duration = time.time() - start_time
        return {
            'success': False,
            'status_code': 0,
            'response_body': '',
            'response_headers': {},
            'error_message': last_error,
            'duration': duration,
        }
    
    @api.model
    def build_redirect_url(self, base_url, params, hash_key='vnp_SecureHash', hash_value=None):
        """
        Generic: Build a full redirect URL with query parameters and hash.
        """
        if not base_url:
            return ''
            
        parts = []
        for key in sorted(params.keys()):
            val = params[key]
            if val is not None and str(val) != '':
                parts.append(f"{urllib.parse.quote_plus(str(key))}={urllib.parse.quote_plus(str(val))}")
                
        if hash_key and hash_value:
            parts.append(f"{urllib.parse.quote_plus(str(hash_key))}={urllib.parse.quote_plus(str(hash_value))}")
            
        query_string = '&'.join(parts)
        separator = '&' if '?' in base_url else '?'
        return f"{base_url}{separator}{query_string}" if query_string else base_url
