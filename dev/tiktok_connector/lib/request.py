import logging
from typing import Optional, Dict, Any
import requests
import json

_logger = logging.getLogger(__name__)


class Request:
    def __init__(self, connector):
        self.connector = connector

    def _make_api_request(self, path: str, body: Optional[Dict[str, Any]] = None, method: str = 'GET', name_request: str = '', query_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Thực hiện API request với authentication và signature
        Hỗ trợ đầy đủ các HTTP methods: GET, POST, PUT, DELETE, PATCH
        """
        config = self.connector._get_config()
        url = config.host + path
        
        headers = {
            "Content-Type": "application/json",
            "x-tts-access-token": config.access_token
        }
        
        try:
            method_upper = method.upper()
            
            if method_upper == 'GET':
                # For GET requests, merge query_params with body
                params = {**(query_params or {}), **(body or {})}
                response = requests.get(url, headers=headers, params=params)
            elif method_upper == 'POST':
                # For POST requests, use query_params for URL and body for request body
                response = requests.post(url, json=body, headers=headers, params=query_params)
            elif method_upper == 'PUT':
                response = requests.put(url, json=body, headers=headers, params=query_params)
            elif method_upper == 'DELETE':
                response = requests.delete(url, json=body, headers=headers, params=query_params)
            elif method_upper == 'PATCH':
                response = requests.patch(url, json=body, headers=headers, params=query_params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            self._create_response(response, method, name_request)
            return response.json()
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"API request failed: {e}")
            raise Exception(f"API request failed: {e}")

    def _create_response(self, response: requests.Response, method: str, name_request: str):
        self.connector.env['tiktok.response'].create({
            'name': name_request,
            'tiktok_connector_id': self.connector._get_config().id,
            'type': method.upper(),
            'response_json': json.dumps(response.json(), indent=4, sort_keys=True)
        })
