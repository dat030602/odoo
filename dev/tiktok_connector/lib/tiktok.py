import logging
import time
from .request import Request
from odoo import models, fields, _
from odoo.exceptions import ValidationError
import logging
import hmac
import time
import requests
import hashlib
import datetime
import hmac
import hashlib
from urllib.parse import urlparse
import json

_logger = logging.getLogger(__name__)


class Tiktok:
    def __init__(self, connector):
        self.request = Request(connector)

    def _make_sign(self, path, query_params=None, body=None, method='POST'):
        """
        Generate signature for TikTok Shop API request
        Based on: https://partner.tiktokshop.com/docv2/page/sign-your-api-request
        
        Args:
            path: API endpoint path (e.g., "/api/v2/shop/get_shop_info")
            query_params: Query parameters dictionary
            body: Request body dictionary
            method: HTTP method (GET, POST, etc.)
        """
        config = self.request.connector._get_config()
        
        # Construct request_option based on actual request data
        request_option = {
            'uri': f"{config.host}{path}",
            'qs': query_params or {},
            'body': body or {},
            'headers': {
                'content-type': 'application/json'
            }
        }
        
        # Step 1: Extract and filter query parameters, exclude "access_token" and "sign", sort alphabetically
        params = request_option.get('qs', {})  
        exclude_keys = ["access_token", "sign"]  
        sorted_params = [  
            {"key": key, "value": str(params[key])}  
            for key in sorted(params.keys())  
            if key not in exclude_keys  
        ]  
    
        # Step 2: Concatenate parameters in {key}{value} format  
        param_string = ''.join([f"{item['key']}{item['value']}" for item in sorted_params])  
        sign_string = param_string  
    
        # Step 3: Append API request path to the signature string  
        uri = request_option.get('uri', '')
        pathname = urlparse(uri).path if uri else path
        sign_string = f"{pathname}{param_string}"  
    
        # Step 4: If not multipart/form-data and request body exists, append JSON-serialized body  
        content_type = request_option.get('headers', {}).get('content-type', '')  
        body_data = request_option.get('body', {})  
        if content_type != 'multipart/form-data' and body_data:  
            body_str = json.dumps(body_data, separators=(',', ':'), sort_keys=True)  # JSON serialization ensures consistency  
            sign_string += body_str  
    
        # Step 5: Wrap signature string with app_secret  
        wrapped_string = f"{config.tiktok_app_secret}{sign_string}{config.tiktok_app_secret}"  
    
        # Step 6: Encode using HMAC-SHA256 and generate hexadecimal signature  
        hmac_obj = hmac.new(  
            config.tiktok_app_secret.encode('utf-8'),  
            wrapped_string.encode('utf-8'),  
            hashlib.sha256  
        )  
        sign = hmac_obj.hexdigest()  
        return sign

    def get_default_params(self, path, method='POST', body=None):
        """
        Get default parameters for TikTok Shop API requests
        Based on TikTok Shop Partner Center common parameters
        """
        config = self.request.connector._get_config()
        
        # Prepare query parameters (for GET requests) or body parameters (for POST requests)
        timestamp = int(time.time())
        query_params = {
            "app_key": config.tiktok_app_key,
            "timestamp": timestamp,
        }
        
        # Add environment-specific parameters
        if config.environment == 'sandbox':
            query_params["test_mode"] = True
        
        # Generate signature with the actual parameters
        sign = self._make_sign(path, query_params, body, method)
        
        # Add signature to parameters
        query_params["sign"] = sign
        
        return query_params

    def _call_api(self, path, name_request, required_params=None, default_params=None, method='POST', **kwargs):
        # Check required parameters
        if required_params:
            for param in required_params:
                if param not in kwargs:
                    raise ValueError(f"{param} is a required parameter")
        
        # Prepare request body/parameters
        request_body = {}
        
        # Add method-specific default parameters if provided
        if default_params:
            request_body.update(default_params)
        
        # Add all kwargs to body (these override defaults)
        request_body.update(kwargs)
        
        # Remove empty parameters
        request_body = {k: v for k, v in request_body.items() if v}
        
        # Get default parameters with signature (for query parameters)
        query_params = self.get_default_params(path, method, request_body if method.upper() == 'POST' else None)
        
        _logger.info(f"{name_request} with query_params: {query_params}")
        _logger.info(f"{name_request} with body: {request_body}")
        
        try:
            # For GET requests, merge query_params with request_body
            if method.upper() == 'GET':
                final_params = {**query_params, **request_body}
                result = self.request._make_api_request(path, final_params, method, name_request=name_request)
            else:
                # For POST/PUT/DELETE requests, use query_params for URL and request_body for body
                result = self.request._make_api_request(path, request_body, method, name_request=name_request, query_params=query_params)
            
            _logger.info(f"Successfully completed {name_request}")
            return result
            
        except Exception as e:
            _logger.error(f"Failed {name_request}: {e}")
            raise

    def get_authorized_category_assets(self, **kwargs):
        """Get authorized category assets from TikTok Shop"""
        return self._call_api(
            path="/api/v2/product/get_authorized_category_assets",
            name_request='Get authorized category assets from TikTok API',
            method='GET',
            **kwargs
        )

    def get_authorized_shops(self, **kwargs):
        """Get authorized shops from TikTok Shop"""
        return self._call_api(
            path="/api/v2/shop/get_authorized_shops",
            name_request='Get authorized shops from TikTok API',
            method='GET',
            **kwargs
        )

    # Order APIs
    def _order_get_order_list(self, **kwargs):
        """Get order list from TikTok Shop"""
        return self._call_api(
            path="/api/v2/order/get_order_list",
            name_request='Get order list from TikTok API',
            method='GET',
            **kwargs
        )

    def _order_get_price_detail(self, **kwargs):
        """Get price detail from TikTok Shop"""
        return self._call_api(
            path="/api/v2/product/get_price_detail",
            name_request='Get price detail from TikTok API',
            method='GET',
            **kwargs
        )

    def _order_add_external_order_references(self, **kwargs):
        """Add external order references to TikTok Shop"""
        return self._call_api(
            path="/api/v2/order/add_external_order_references",
            name_request='Add external order references to TikTok API',
            method='POST',
            **kwargs
        )

    def _order_get_external_order_references(self, **kwargs):
        """Get external order references from TikTok Shop"""
        return self._call_api(
            path="/api/v2/order/get_external_order_references",
            name_request='Get external order references from TikTok API',
            method='GET',
            **kwargs
        )

    def _order_search_order_by_external_order_reference(self, **kwargs):
        """Search order by external order reference from TikTok Shop"""
        return self._call_api(
            path="/api/v2/order/search_order_by_external_order_reference",
            name_request='Search order by external order reference from TikTok API',
            method='GET',
            **kwargs
        )

    def _order_get_order_detail(self, **kwargs):
        """Get order detail from TikTok Shop"""
        return self._call_api(
            path="/api/v2/order/get_order_detail",
            name_request='Get order detail from TikTok API',
            method='GET',
            **kwargs
        )
