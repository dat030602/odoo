import logging
from typing import Optional, Dict, Any
import requests
import json

_logger = logging.getLogger(__name__)


class Request:
    def __init__(self, connector):
        self.connector = connector

    def _make_api_request(self, path: str, body: Optional[Dict[str, Any]] = None, method: str = 'GET', name_request: str = '') -> Dict[str, Any]:
        """
        Thực hiện API request với authentication
        Hỗ trợ đầy đủ các HTTP methods: GET, POST, PUT, DELETE, PATCH
        """
        url = self.connector._get_url_request(path)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.connector._get_config().access_token}"
        }
        
        try:
            method_upper = method.upper()
            
            if method_upper == 'GET':
                response = requests.get(url, headers=headers, params=body)
            elif method_upper == 'POST':
                response = requests.post(url, json=body, headers=headers)
            elif method_upper == 'PUT':
                response = requests.put(url, json=body, headers=headers)
            elif method_upper == 'DELETE':
                response = requests.delete(url, json=body, headers=headers)
            elif method_upper == 'PATCH':
                response = requests.patch(url, json=body, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            self._create_response(response, method, name_request)
            return response.json()
            
        except requests.exceptions.RequestException as e:
            _logger.error(f"API request failed: {e}")
            raise Exception(f"API request failed: {e}")

    def _create_response(self, response: requests.Response, method: str, name_request: str):
        self.connector.env['shopee.response'].create({
            'name': name_request,
            'shopee_connector_id': self.connector._get_config().id,
            'type': method.upper(),
            'response_json': json.dumps(response.json(), indent=4, sort_keys=True)
        })
