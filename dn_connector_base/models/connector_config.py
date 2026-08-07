"""
Connector Config
================
Configuration model for REST API connections. Supports multiple authentication
strategies including Bearer, Basic, API Key, OAuth2, and custom code-based auth.
"""

import base64
import json
import logging
from datetime import timedelta

import requests

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ConnectorConfig(models.Model):
    """Configuration for a REST API connection.

    Stores base URL, authentication credentials, default headers, and sync
    settings. Each config can have multiple endpoints defined via the
    endpoint_ids One2many field.
    """

    _name = "connector.config"
    _description = "Configuration for a REST API connection"

    name = fields.Char(
        string="Name",
        required=True,
        help="A descriptive name for this connector configuration.",
    )
    base_url = fields.Char(
        string="Base URL",
        required=True,
        help="The base URL of the REST API (e.g., https://api.example.com).",
    )
    auth_type = fields.Selection(
        [
            ("none", "None"),
            ("bearer", "Bearer Token"),
            ("basic", "Basic Auth"),
            ("api_key", "API Key"),
            ("oauth2", "OAuth2"),
            ("custom", "Custom (code)"),
        ],
        string="Authentication Type",
        default="none",
        required=True,
        help="The authentication method to use for API requests.",
    )

    # Bearer / API Key
    token = fields.Char(
        string="Token",
        groups="base.group_system",
        help="The bearer token or API key value.",
    )
    api_key_header = fields.Char(
        string="API Key Header",
        default="X-API-Key",
        help="The HTTP header name for API key authentication.",
    )

    # Basic Auth
    username = fields.Char(
        string="Username",
        help="Username for Basic authentication.",
    )
    password = fields.Char(
        string="Password",
        groups="base.group_system",
        help="Password for Basic authentication.",
    )

    # OAuth2
    oauth_client_id = fields.Char(
        string="Client ID",
        help="OAuth2 client ID.",
    )
    oauth_client_secret = fields.Char(
        string="Client Secret",
        groups="base.group_system",
        help="OAuth2 client secret.",
    )
    oauth_token_url = fields.Char(
        string="Token URL",
        help="OAuth2 token endpoint URL.",
    )
    oauth_access_token = fields.Char(
        string="Access Token",
        groups="base.group_system",
        help="Current OAuth2 access token.",
    )
    oauth_refresh_token = fields.Char(
        string="Refresh Token",
        groups="base.group_system",
        help="OAuth2 refresh token.",
    )
    oauth_expires_at = fields.Datetime(
        string="Expires At",
        help="Expiration time of the current access token.",
    )

    default_headers = fields.Text(
        string="Default Headers",
        help="JSON dict of default headers, e.g. {\"Content-Type\": \"application/json\"}.",
    )
    endpoint_ids = fields.One2many(
        "connector.endpoint",
        "connector_id",
        string="Endpoints",
        help="List of endpoints associated with this connector.",
    )
    auto_create_schema = fields.Boolean(
        string="Auto Create Schema",
        default=True,
        help="If enabled, automatically discover and create models/fields/views from API responses.",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        help="If unchecked, this connector configuration is disabled.",
    )

    def _get_auth_headers(self):
        """Return a dictionary of authentication headers for API requests.

        Handles Bearer, Basic, API Key, and OAuth2 authentication types.
        For OAuth2, automatically refreshes the token if it has expired.

        :return: A dict of HTTP headers containing authentication information.
        :raises ValidationError: If OAuth2 refresh fails.
        """
        self.ensure_one()
        headers = {}
        if self.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.auth_type == "basic":
            raw = f"{self.username}:{self.password}".encode()
            headers["Authorization"] = f"Basic {base64.b64encode(raw).decode()}"
        elif self.auth_type == "api_key":
            headers[self.api_key_header] = self.token
        elif self.auth_type == "oauth2":
            if not self.oauth_access_token or (
                self.oauth_expires_at
                and self.oauth_expires_at <= fields.Datetime.now()
            ):
                self._oauth2_refresh()
            headers["Authorization"] = f"Bearer {self.oauth_access_token}"
        return headers

    def _oauth2_refresh(self):
        """Refresh the OAuth2 access token using the refresh token.

        Sends a POST request to the OAuth2 token URL with the refresh token
        and updates the stored access token, refresh token, and expiration time.

        :raises ValidationError: If the token refresh request fails.
        """
        self.ensure_one()
        resp = requests.post(
            self.oauth_token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.oauth_refresh_token,
                "client_id": self.oauth_client_id,
                "client_secret": self.oauth_client_secret,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self.sudo().write({
            "oauth_access_token": data["access_token"],
            "oauth_refresh_token": data.get(
                "refresh_token", self.oauth_refresh_token
            ),
            "oauth_expires_at": fields.Datetime.now()
            + timedelta(seconds=data.get("expires_in", 3600)),
        })

    def _get_default_headers(self):
        """Parse and return the default headers from JSON text.

        :return: A dict of default HTTP headers, or an empty dict if none configured.
        """
        self.ensure_one()
        if self.default_headers:
            try:
                return json.loads(self.default_headers)
            except (json.JSONDecodeError, TypeError):
                _logger.warning(
                    "Invalid JSON in default_headers for connector %s",
                    self.name,
                )
        return {}

    def _request(self, method, path, params=None, json_body=None, extra_headers=None):
        """Send an HTTP request to the configured API endpoint.

        Combines authentication headers, default headers, and any extra headers
        before sending the request. Returns the parsed JSON response.

        :param method: HTTP method (GET, POST, PUT, PATCH, DELETE).
        :param path: API path (appended to base_url).
        :param params: Query parameters dict.
        :param json_body: JSON body for POST/PUT/PATCH requests.
        :param extra_headers: Additional headers to include in the request.
        :return: The parsed JSON response as a dict.
        :raises ValidationError: If the request fails or returns an error status.
        """
        self.ensure_one()
        url = f"{self.base_url.rstrip('/')}{path}"
        headers = {}
        headers.update(self._get_default_headers())
        headers.update(self._get_auth_headers())
        if extra_headers:
            headers.update(extra_headers)

        try:
            resp = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
            if resp.content:
                return resp.json()
            return {}
        except requests.exceptions.RequestException as e:
            _logger.exception("Request failed for %s %s", method, url)
            raise ValidationError(
                _("Request failed: %s %s\n%s") % (method, url, str(e))
            ) from e
