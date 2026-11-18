import json
import re
from odoo import api, fields, models


class MisaApiLog(models.Model):
    _name = 'misa.api.log'
    _description = 'MISA API Request Log'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Description', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    service_type = fields.Selection([
        ('meinvoice', 'meInvoice (Publishing)'),
        ('inbot', 'INBOT (Input/Output)')
    ], string='Service', required=True, default='meinvoice', index=True)

    endpoint = fields.Char(string='Endpoint URL', required=True)
    http_method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE')
    ], string='HTTP Method', default='POST', required=True)

    request_headers = fields.Text(string='Request Headers')
    request_body = fields.Text(string='Request Body')
    response_status = fields.Integer(string='Status Code')
    response_body = fields.Text(string='Response Body')
    duration = fields.Float(string='Duration (s)', digits=(6, 3))

    is_success = fields.Boolean(string='Success', index=True)
    error_code = fields.Char(string='Error Code', index=True)
    error_message = fields.Text(string='Error Message')

    @api.model
    def _mask_sensitive_data(self, data_str):
        """Mask password, secret, and authorization tokens from logs."""
        if not data_str:
            return data_str

        # Patterns for json / dict keys
        patterns = [
            (r'("password"\s*:\s*)"([^"]+)"', r'\1"***"'),
            (r'("PassWord"\s*:\s*)"([^"]+)"', r'\1"***"'),
            (r'("ClientSecret"\s*:\s*)"([^"]+)"', r'\1"***"'),
            (r'("client_secret"\s*:\s*)"([^"]+)"', r'\1"***"'),
            (r'("securetoken"\s*:\s*)"([^"]+)"', r'\1"***"'),
            (r'("Authorization"\s*:\s*)"Bearer [^"]+"', r'\1"Bearer ***"'),
            (r"('password'\s*:\s*)'([^']+)'", r"\1'***'"),
            (r"('PassWord'\s*:\s*)'([^']+)'", r"\1'***'"),
            (r"('ClientSecret'\s*:\s*)'([^']+)'", r"\1'***'"),
            (r"('securetoken'\s*:\s*)'([^']+)'", r"\1'***'"),
        ]

        masked = str(data_str)
        for pattern, replacement in patterns:
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)
        return masked

    @api.model
    def create_log(self, company, service_type, endpoint, http_method, headers, request_body,
                   response_status, response_body, duration, is_success, error_code=None, error_message=None):
        """Create a new API log with sensitive information scrubbed."""
        masked_headers = self._mask_sensitive_data(json.dumps(headers, indent=2) if isinstance(headers, dict) else str(headers or ''))
        masked_body = self._mask_sensitive_data(request_body)

        summary_name = f"[{service_type.upper()}] {http_method} {endpoint.split('?')[0].split('/')[-1] or endpoint}"

        return self.create({
            'name': summary_name,
            'company_id': company.id,
            'service_type': service_type,
            'endpoint': endpoint,
            'http_method': http_method,
            'request_headers': masked_headers,
            'request_body': masked_body,
            'response_status': response_status,
            'response_body': response_body,
            'duration': duration,
            'is_success': is_success,
            'error_code': error_code,
            'error_message': error_message,
        })
