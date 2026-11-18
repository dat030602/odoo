import json
import logging
import time
from datetime import datetime, timedelta
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    # General / Shared fields
    misa_tax_code = fields.Char(string='Tax Code', help='Company Tax Code registered with MISA')
    misa_username = fields.Char(string='Username / Account', help='MISA login username/email/phone')
    misa_password = fields.Char(string='Password', help='MISA login password')
    misa_client_id = fields.Char(string='Client ID', help='ClientID provided by MISA')
    misa_client_secret = fields.Char(string='Client Secret', help='ClientSecret provided by MISA')
    misa_device_id = fields.Char(string='Device ID', help='Device ID identifier for 2FA and authentication')
    misa_otp_code = fields.Char(string='OTP Code (2FA)', help='Temporary OTP code for completing 2FA challenge')

    # meInvoice Connection Configuration
    misa_meinvoice_base_url = fields.Char(
        string='meInvoice Base URL',
        default='https://developer.misa.vn/apis/itg/meinvoice/',
        help='Base URL for MISA meInvoice API endpoints'
    )
    misa_meinvoice_token = fields.Char(string='Publish Token Cache', help='Access token used for publishing e-invoices')
    misa_meinvoice_token_draft = fields.Char(string='Draft Token Cache', help='Access token used for draft/preview e-invoices')
    misa_meinvoice_token_expiry = fields.Datetime(string='meInvoice Token Expiry')
    misa_meinvoice_user_id = fields.Char(string='meInvoice User ID (2FA)', help='CustomData.Id returned from meInvoice login')

    # INBOT Connection Configuration
    misa_inbot_base_url = fields.Char(
        string='INBOT Base URL',
        default='https://developer.misa.vn/apis',
        help='Base URL for MISA INBOT API endpoints'
    )
    misa_inbot_subscribers_id = fields.Char(string='Subscribers ID (CompanyID)', help='SubscribersId / CompanyID in MISA INBOT')
    misa_inbot_secure_token = fields.Char(string='INBOT Secure Token', help='Intermediate secure token returned from ValidateUser')
    misa_inbot_jwt_token = fields.Char(string='INBOT JWT Token', help='JWT Access Token used for INBOT requests')
    misa_inbot_token_expiry = fields.Datetime(string='INBOT Token Expiry')

    # Subscription / Quota monitoring
    misa_inbot_product_pack_code = fields.Char(string='Pack Code', readonly=True)
    misa_inbot_pack_start_date = fields.Date(string='Pack Start Date', readonly=True)
    misa_inbot_pack_expired_date = fields.Date(string='Pack Expired Date', readonly=True)
    misa_inbot_number_of_invoice = fields.Integer(string='Quota Invoices', readonly=True)
    misa_inbot_number_inv_used = fields.Integer(string='Invoices Used', readonly=True)
    misa_inbot_number_inv_still = fields.Integer(string='Invoices Remaining', readonly=True)
    misa_inbot_pack_status = fields.Selection([
        ('0', 'Official (Standard)'),
        ('1', 'Official (Active)'),
        ('2', 'Trial'),
    ], string='Pack Status', readonly=True)

    # -------------------------------------------------------------------------
    # Helper: HTTP Request with logging
    # -------------------------------------------------------------------------
    def _misa_request(self, service_type, endpoint, method='GET', headers=None, json_data=None, data=None, params=None):
        """Unified request executor logging into misa.api.log."""
        self.ensure_one()
        url = endpoint
        if not (url.startswith('http://') or url.startswith('https://')):
            base = self.misa_meinvoice_base_url if service_type == 'meinvoice' else self.misa_inbot_base_url
            url = f"{base.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = headers or {}
        req_body = json.dumps(json_data, ensure_ascii=False) if json_data else (data if isinstance(data, str) else json.dumps(data) if data else None)

        start_time = time.time()
        is_success = False
        error_code = None
        error_message = None
        status_code = 0
        resp_text = ''
        res_json = None

        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data if not json_data else None,
                json=json_data,
                params=params,
                timeout=45
            )
            duration = time.time() - start_time
            status_code = resp.status_code
            resp_text = resp.text

            try:
                res_json = resp.json()
            except Exception:
                res_json = None

            if 200 <= status_code < 300:
                is_success = True
                if isinstance(res_json, dict):
                    if res_json.get('Success') is False or res_json.get('success') is False:
                        is_success = False
                        error_code = str(res_json.get('ErrorCode') or res_json.get('Code') or res_json.get('errorCode') or '')
                        error_message = str(res_json.get('Error') or res_json.get('Errors') or res_json.get('Message') or res_json.get('description') or '')
            else:
                is_success = False
                error_code = str(status_code)
                if isinstance(res_json, dict):
                    error_code = str(res_json.get('ErrorCode') or res_json.get('Code') or status_code)
                    error_message = str(res_json.get('Error') or res_json.get('Errors') or res_json.get('Message') or resp_text)
                else:
                    error_message = resp_text

        except Exception as e:
            duration = time.time() - start_time
            is_success = False
            error_code = 'EX_REQUEST'
            error_message = str(e)
            resp_text = str(e)

        # Log into misa.api.log
        self.env['misa.api.log'].sudo().create_log(
            company=self,
            service_type=service_type,
            endpoint=url,
            http_method=method,
            headers=headers,
            request_body=req_body,
            response_status=status_code,
            response_body=resp_text,
            duration=duration,
            is_success=is_success,
            error_code=error_code,
            error_message=error_message,
        )

        return {
            'status_code': status_code,
            'is_success': is_success,
            'data': res_json if res_json is not None else resp_text,
            'error_code': error_code,
            'error_message': error_message,
        }

    # -------------------------------------------------------------------------
    # meInvoice Authentication Flows
    # -------------------------------------------------------------------------
    def action_get_meinvoice_token(self, is_draft=False, force_refresh=False):
        """Fetch or refresh Bearer token for meInvoice."""
        self.ensure_one()
        now = fields.Datetime.now()
        cache_field = 'misa_meinvoice_token_draft' if is_draft else 'misa_meinvoice_token'
        cached_token = getattr(self, cache_field)

        if not force_refresh and cached_token and self.misa_meinvoice_token_expiry and self.misa_meinvoice_token_expiry > (now + timedelta(minutes=10)):
            return cached_token

        if not self.misa_client_id or not self.misa_tax_code or not self.misa_username or not self.misa_password:
            raise UserError(_("Please configure ClientID, Tax Code, Username, and Password on Company %s.") % self.name)

        headers = {
            'ClientID': self.misa_client_id,
            'Content-Type': 'application/json',
        }
        if self.misa_client_secret:
            headers['ClientSecret'] = self.misa_client_secret

        body = {
            'taxcode': self.misa_tax_code,
            'username': self.misa_username,
            'password': self.misa_password,
        }

        # Handle draft invoice flow if separate endpoint/flag
        endpoint = 'invoice/token'
        res = self._misa_request(
            service_type='meinvoice',
            endpoint=endpoint,
            method='POST',
            headers=headers,
            json_data=body
        )

        if not res['is_success']:
            raise UserError(_("Failed to authenticate with MISA meInvoice: %s (%s)") % (res['error_message'], res['error_code']))

        res_data = res['data']
        # Check if 2FA is required
        custom_data = res_data.get('CustomData') if isinstance(res_data, dict) else None
        if isinstance(custom_data, dict) and custom_data.get('Id'):
            self.misa_meinvoice_user_id = str(custom_data.get('Id'))

        token = res_data.get('Data') if isinstance(res_data, dict) else None
        if not token:
            token = res_data.get('token') or res_data.get('access_token')

        if not token:
            # Check if 2FA code is needed
            if custom_data and custom_data.get('Id'):
                raise UserError(_("2FA is enabled for this MISA meInvoice account. Please enter the OTP code and click 'Verify 2FA'."))
            raise UserError(_("No access token returned from MISA meInvoice: %s") % res['data'])

        # Tokens normally valid for 14 days
        expiry = now + timedelta(days=14)
        vals = {
            cache_field: token,
            'misa_meinvoice_token_expiry': expiry,
        }
        if not is_draft and not self.misa_meinvoice_token_draft:
            vals['misa_meinvoice_token_draft'] = token

        self.write(vals)
        return token

    def action_verify_meinvoice_2fa(self):
        """Submit OTP 2FA challenge to meInvoice."""
        self.ensure_one()
        if not self.misa_otp_code:
            raise UserError(_("Please enter the OTP Code received via SMS/Email/App."))
        if not self.misa_meinvoice_user_id:
            raise UserError(_("Missing meInvoice User ID. Please click 'Get meInvoice Token' first to initiate login."))

        headers = {
            'ClientID': self.misa_client_id or '',
            'Content-Type': 'application/json',
        }
        if self.misa_client_secret:
            headers['ClientSecret'] = self.misa_client_secret

        body = {
            'UserID': self.misa_meinvoice_user_id,
            'Code': self.misa_otp_code,
            'DeviceID': self.misa_device_id or 'ODOO_SERVER_DEFAULT',
            'Remember': True,
        }

        res = self._misa_request(
            service_type='meinvoice',
            endpoint='invoice/2fa',
            method='POST',
            headers=headers,
            json_data=body
        )

        if not res['is_success']:
            raise UserError(_("2FA Verification failed: %s (%s)") % (res['error_message'], res['error_code']))

        res_data = res['data']
        token = res_data.get('Data') if isinstance(res_data, dict) else None
        if not token:
            token = res_data.get('token') or res_data.get('access_token')

        if not token:
            raise UserError(_("2FA verified but no token returned: %s") % res['data'])

        now = fields.Datetime.now()
        self.write({
            'misa_meinvoice_token': token,
            'misa_meinvoice_token_draft': token,
            'misa_meinvoice_token_expiry': now + timedelta(days=14),
            'misa_otp_code': False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('2FA verified and token updated successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_refresh_meinvoice_token(self):
        """Refresh meInvoice token using /invoice/token/refresh."""
        self.ensure_one()
        token = self.misa_meinvoice_token
        if not token:
            return self.action_get_meinvoice_token(force_refresh=True)

        headers = {
            'ClientID': self.misa_client_id or '',
            'Authorization': f"Bearer {token}",
            'Content-Type': 'application/json',
        }
        if self.misa_client_secret:
            headers['ClientSecret'] = self.misa_client_secret

        expiry_str = fields.Datetime.to_string(self.misa_meinvoice_token_expiry or fields.Datetime.now())
        body = {
            'tokenExpriedDate': expiry_str,
        }

        res = self._misa_request(
            service_type='meinvoice',
            endpoint='invoice/token/refresh',
            method='POST',
            headers=headers,
            json_data=body
        )

        if res['is_success'] and isinstance(res['data'], dict) and res['data'].get('Data'):
            new_token = res['data']['Data']
            now = fields.Datetime.now()
            self.write({
                'misa_meinvoice_token': new_token,
                'misa_meinvoice_token_expiry': now + timedelta(days=14),
            })
            return new_token
        else:
            # Fallback to full login
            return self.action_get_meinvoice_token(force_refresh=True)

    # -------------------------------------------------------------------------
    # INBOT Authentication Flows (2-step: validateuser -> jwttoken)
    # -------------------------------------------------------------------------
    def action_get_inbot_jwt_token(self, force_refresh=False):
        """2-step authentication flow to retrieve INBOT JWT token."""
        self.ensure_one()
        now = fields.Datetime.now()
        if not force_refresh and self.misa_inbot_jwt_token and self.misa_inbot_token_expiry and self.misa_inbot_token_expiry > (now + timedelta(minutes=10)):
            return self.misa_inbot_jwt_token

        if not self.misa_client_id or not self.misa_tax_code or not self.misa_username or not self.misa_password:
            raise UserError(_("Please configure ClientID, Tax Code, Username, and Password on Company %s.") % self.name)

        # Step 1: ValidateUser
        headers_step1 = {
            'ClientID': self.misa_client_id,
            'CompanyTaxCode': self.misa_tax_code,
            'UserName': self.misa_username,
            'Content-Type': 'application/json',
        }
        body_step1 = {
            'PassWord': self.misa_password,
        }

        res1 = self._misa_request(
            service_type='inbot',
            endpoint='meinvoicebot/v1/validateuser',
            method='POST',
            headers=headers_step1,
            json_data=body_step1
        )

        if not res1['is_success']:
            raise UserError(_("INBOT ValidateUser failed: %s (%s)") % (res1['error_message'], res1['error_code']))

        # Data format: "{CompanyID};{securetoken}"
        data_str = res1['data'].get('Data') if isinstance(res1['data'], dict) else ''
        if not data_str or ';' not in str(data_str):
            raise UserError(_("Unexpected ValidateUser response format (expected 'CompanyID;securetoken'): %s") % res1['data'])

        parts = str(data_str).split(';')
        company_id = parts[0].strip()
        secure_token = parts[1].strip()

        # Step 2: Get JWT Token
        headers_step2 = {
            'ClientID': self.misa_client_id,
            'companytaxcode': self.misa_tax_code,
            'username': self.misa_username,
            'securetoken': secure_token,
            'Content-Type': 'application/json',
        }

        res2 = self._misa_request(
            service_type='inbot',
            endpoint='meinvoicebot/v1/auth/jwttoken',
            method='POST',
            headers=headers_step2
        )

        if not res2['is_success']:
            raise UserError(_("INBOT JWT Token retrieval failed: %s (%s)") % (res2['error_message'], res2['error_code']))

        res2_data = res2['data']
        jwt_token = None
        if isinstance(res2_data, dict):
            jwt_token = res2_data.get('Data') or res2_data.get('AccessToken') or res2_data.get('token')
        if not jwt_token:
            raise UserError(_("No AccessToken found in INBOT JWT response: %s") % res2_data)

        # JWT tokens usually expire in 24 hours or specified by expiry
        self.write({
            'misa_inbot_subscribers_id': company_id,
            'misa_inbot_secure_token': secure_token,
            'misa_inbot_jwt_token': jwt_token,
            'misa_inbot_token_expiry': now + timedelta(hours=23),
        })

        return jwt_token

    def _execute_inbot_api(self, endpoint, method='GET', headers=None, json_data=None, data=None, params=None):
        """Execute an INBOT request with automatic re-authentication if token expires."""
        self.ensure_one()
        jwt_token = self.action_get_inbot_jwt_token()
        headers = headers or {}
        headers['Authorization'] = f"Bearer {jwt_token}"
        headers['ClientID'] = self.misa_client_id or ''

        res = self._misa_request('inbot', endpoint, method=method, headers=headers, json_data=json_data, data=data, params=params)

        # Check for expired/invalid token codes
        err_code = str(res.get('error_code') or '')
        err_msg = str(res.get('error_message') or '')
        expired_patterns = ['TokenExpiredCode', 'InvalidTokenCode', 'INVALIDTOKEN', 'TOKENEXPIRED', '401']

        if any(p in err_code for p in expired_patterns) or any(p in err_msg for p in expired_patterns):
            _logger.info("INBOT Token expired or invalid (%s), re-authenticating...", err_code)
            new_token = self.action_get_inbot_jwt_token(force_refresh=True)
            headers['Authorization'] = f"Bearer {new_token}"
            res = self._misa_request('inbot', endpoint, method=method, headers=headers, json_data=json_data, data=data, params=params)

        return res

    # -------------------------------------------------------------------------
    # Test Connection Actions
    # -------------------------------------------------------------------------
    def action_test_meinvoice_connection(self):
        """Test connection to MISA meInvoice by requesting token."""
        self.ensure_one()
        token = self.action_get_meinvoice_token(force_refresh=True)
        if token:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Successfully connected to MISA meInvoice API and obtained Bearer Token.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_test_inbot_connection(self):
        """Test connection to MISA INBOT by executing 2-step authentication."""
        self.ensure_one()
        jwt_token = self.action_get_inbot_jwt_token(force_refresh=True)
        if jwt_token:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Successfully connected to MISA INBOT API and obtained JWT Token. SubscribersId: %s') % (self.misa_inbot_subscribers_id or 'N/A'),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_sync_inbot_subscribers_and_organizations(self):
        """Resolve SubscribersId and synchronize Organizations."""
        self.ensure_one()
        # Fetch SubscribersId if empty
        if not self.misa_inbot_subscribers_id and self.misa_tax_code:
            endpoint = f"meinvoicebot/v1/subscribers/code/{self.misa_tax_code}"
            res = self._execute_inbot_api(endpoint, method='GET')
            if res['is_success'] and isinstance(res['data'], dict):
                sub_id = res['data'].get('Data', {}).get('Id') if isinstance(res['data'].get('Data'), dict) else res['data'].get('Id')
                if sub_id:
                    self.misa_inbot_subscribers_id = str(sub_id)

        # Trigger organization sync
        return self.env['misa.organization'].sync_organizations(self)
