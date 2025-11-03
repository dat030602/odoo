# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import urllib.parse
import datetime
import uuid
import socket
import hmac
import hashlib
import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('vnpay_token', "VNPay Token")], ondelete={'vnpay_token': 'set default'})
    
    # VNPay Token specific fields - sử dụng chung field từ payment_vnpay
    # vnpay_tmn_code và vnpay_hash_secret_key sẽ được kế thừa từ payment_vnpay
    
    # VNPay Token Configuration Constants - sử dụng chung field từ payment_vnpay
    vnpay_token_return_url = fields.Char(string="Token Return URL", default='/payment/vnpay_token/token-return/')
    vnpay_token_cancel_url = fields.Char(string="Token Cancel URL", default='/payment/vnpay_token/token-cancel/')
    vnpay_token_webhook_url = fields.Char(string="Token Webhook URL", default='/payment/vnpay_token/token-webhook/')
    vnpay_token_create_url = fields.Char(string="Token Create URL", default="https://sandbox.vnpayment.vn/token_ui/create-token.html")
    vnpay_token_pay_url = fields.Char(string="Token Pay URL", default="https://sandbox.vnpayment.vn/token_ui/pay-token.html")
    vnpay_token_delete_url = fields.Char(string="Token Delete URL", default="https://sandbox.vnpayment.vn/token_ui/delete-token.html")
    # Sử dụng chung field từ payment_vnpay - sẽ được kế thừa từ module payment_vnpay
    # Các field này sẽ được sử dụng trực tiếp từ payment_vnpay module

    # === COMPUTE METHODS ===#

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to configure view fields for VNPay Token.

        :return: None
        """
        # First call the parent method to set default values
        # Then override specific fields for VNPay Token providers
        super(PaymentProvider, self)._compute_view_configuration_fields()
        for provider in self:
            if provider.code == 'vnpay_token':
                provider.show_credentials_page = True
                provider.show_allow_tokenization = True
                provider.show_allow_express_checkout = False  # VNPay Token doesn't support express checkout
                provider.show_pre_msg = True
                provider.show_pending_msg = True
                provider.show_auth_msg = True
                provider.show_done_msg = True
                provider.show_cancel_msg = True
                provider.require_currency = False
            else:
                provider.show_credentials_page = provider.show_credentials_page
                provider.show_allow_tokenization = provider.show_allow_tokenization
                provider.show_allow_express_checkout = provider.show_allow_express_checkout
                provider.show_pre_msg = provider.show_pre_msg
                provider.show_pending_msg = provider.show_pending_msg
                provider.show_auth_msg = provider.show_auth_msg
                provider.show_done_msg = provider.show_done_msg
                provider.show_cancel_msg = provider.show_cancel_msg
                provider.require_currency = provider.require_currency

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        res = super(PaymentProvider, self)._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'vnpay_token').update({
            'support_express_checkout': False,
            'support_manual_capture': False,
            'support_tokenization': True,  # Enable tokenization for VNPay Token
            'support_refund': 'full_only',
        })
        return res

    @api.onchange('state')
    def _onchange_vnpay_token_state(self):
        """Update URLs based on state selection - sử dụng chung với payment_vnpay."""
        if self.code == 'vnpay_token':
            if self.state == 'test':
                self.vnpay_token_create_url = "https://sandbox.vnpayment.vn/token_ui/create-token.html"
                self.vnpay_token_pay_url = "https://sandbox.vnpayment.vn/token_ui/pay-token.html"
                self.vnpay_token_delete_url = "https://sandbox.vnpayment.vn/token_ui/delete-token.html"
                # Sử dụng chung field từ payment_vnpay
                self.vnpay_api_url = "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction"
            elif self.state == 'enabled':
                self.vnpay_token_create_url = "https://vnpayment.vn/token_ui/create-token.html"
                self.vnpay_token_pay_url = "https://vnpayment.vn/token_ui/pay-token.html"
                self.vnpay_token_delete_url = "https://vnpayment.vn/token_ui/delete-token.html"
                # Sử dụng chung field từ payment_vnpay
                self.vnpay_api_url = "https://vnpayment.vn/merchant_webapi/api/transaction"

    # === CONSTRAINT METHODS ===#

    @api.constrains('state', 'vnpay_tmn_code', 'vnpay_hash_secret_key')
    def _check_state_of_connected_account_is_never_test(self):
        """ Check that the provider of a connected account can never been set to 'test'.

        :return: None
        :raise ValidationError: If the provider of a connected account is set in state 'test'.
        """
        if self.filtered(lambda p: p.code == 'vnpay_token' and p.state in ('test', 'enabled')):
            if self.vnpay_tmn_code == '' or self.vnpay_hash_secret_key == '':
                raise UserError(_("User must enter the TMN code and Hash Secret Key."))

    # === BUSINESS METHODS - VNPAY TOKEN FLOW === #

    def _generate_query_string_vnpay_token(self, query):
        """Generate query string for VNPay Token API."""
        inputData = json.loads(json.dumps(query, sort_keys=True))
        keys = inputData.keys()
        query_string = ''
        seq = 0
        for key in keys:
            if seq == 1:
                query_string = query_string + "&" + key + '=' + urllib.parse.quote_plus(str(inputData[key]))
            else:
                seq = 1
                query_string = key + '=' + urllib.parse.quote_plus(str(inputData[key]))
        return query_string

    def _generate_url_vnpay_token(self, params, operation='create'):
        """Generate VNPay Token URL based on operation."""
        provider = self.search([('code', '=', 'vnpay_token')], limit=1)
        query_string = self._generate_query_string_vnpay_token(params)
        
        if operation == 'create':
            return provider.vnpay_token_create_url + "?" + query_string
        elif operation == 'pay':
            return provider.vnpay_token_pay_url + "?" + query_string
        elif operation == 'delete':
            return provider.vnpay_token_delete_url + "?" + query_string
        return provider.vnpay_token_create_url + "?" + query_string

    def _prepare_token_create_payload(self, partner_id, transaction_reference=None):
        """Prepare payload for token creation."""
        provider = self.search([('code', '=', 'vnpay_token')], limit=1)
        ip_address = self.env['ir.config_parameter'].sudo().get_param('payment_vnpay_token.ip_address')
        base_url = self.get_base_url()
        vnp_Locale = 'en' if self.env.lang == 'en_US' else 'vn'
        
        # Use provided transaction reference or generate one
        if transaction_reference:
            txn_ref = transaction_reference
        else:
            txn_ref = str(uuid.uuid4().hex[:16])
            
        date = datetime.datetime.now().astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        
        payload = {
            'vnp_version': provider.vnpay_version,  # Sử dụng chung field từ payment_vnpay
            'vnp_command': 'token_create',
            'vnp_tmn_code': provider.vnpay_tmn_code,  # Sử dụng chung field từ payment_vnpay
            'vnp_app_user_id': str(partner_id),
            'vnp_card_type': '01',  # Nội địa: 01, Quốc tế: 02
            'vnp_txn_ref': txn_ref,
            'vnp_txn_desc': f"Create token for user {partner_id}",
            'vnp_return_url': urllib.parse.urljoin(base_url, provider.vnpay_token_return_url),
            'vnp_cancel_url': urllib.parse.urljoin(base_url, provider.vnpay_token_cancel_url),
            'vnp_ip_addr': ip_address,
            'vnp_create_date': date.strftime('%Y%m%d%H%M%S'),
            'vnp_locale': vnp_Locale,
        }
        
        query_string = self._generate_query_string_vnpay_token(payload)
        payload['vnp_secure_hash'] = self._hmacsha512_token(query_string)
        return payload

    def _prepare_token_pay_payload(self, token, amount, transaction_reference=None):
        """Prepare payload for token payment."""
        provider = self.search([('code', '=', 'vnpay_token')], limit=1)
        ip_address = self.env['ir.config_parameter'].sudo().get_param('payment_vnpay_token.ip_address')
        base_url = self.get_base_url()
        vnp_Locale = 'en' if self.env.lang == 'en_US' else 'vn'
        
        if amount:
            amount = int(amount) * 100
            
        # Use provided transaction reference or generate one
        if transaction_reference:
            txn_ref = transaction_reference
        else:
            txn_ref = str(uuid.uuid4().hex[:16])
            
        date = datetime.datetime.now().astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        
        payload = {
            'vnp_version': provider.vnpay_version,  # Sử dụng chung field từ payment_vnpay
            'vnp_command': 'token_pay',
            'vnp_tmn_code': provider.vnpay_tmn_code,  # Sử dụng chung field từ payment_vnpay
            'vnp_token': token.provider_ref,  # VNPay token from stored token
            'vnp_amount': amount,
            'vnp_curr_code': provider.vnpay_currency_code,  # Sử dụng chung field từ payment_vnpay
            'vnp_txn_ref': txn_ref,
            'vnp_order_info': f"Payment with token: {txn_ref}",
            'vnp_order_type': 'billpayment',
            'vnp_locale': vnp_Locale,
            'vnp_create_date': date.strftime('%Y%m%d%H%M%S'),
            'vnp_expire_date': (date + datetime.timedelta(minutes=15)).strftime('%Y%m%d%H%M%S'),
            'vnp_ip_addr': ip_address,
            'vnp_return_url': urllib.parse.urljoin(base_url, provider.vnpay_token_return_url),
        }
        
        query_string = self._generate_query_string_vnpay_token(payload)
        payload['vnp_secure_hash'] = self._hmacsha512_token(query_string)
        return payload

    def _prepare_token_delete_payload(self, token):
        """Prepare payload for token deletion."""
        provider = self.search([('code', '=', 'vnpay_token')], limit=1)
        ip_address = self.env['ir.config_parameter'].sudo().get_param('payment_vnpay_token.ip_address')
        base_url = self.get_base_url()
        
        date = datetime.datetime.now().astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        
        payload = {
            'vnp_version': provider.vnpay_version,  # Sử dụng chung field từ payment_vnpay
            'vnp_command': 'token_delete',
            'vnp_tmn_code': provider.vnpay_tmn_code,  # Sử dụng chung field từ payment_vnpay
            'vnp_token': token.provider_ref,
            'vnp_app_user_id': str(token.partner_id.id),
            'vnp_ip_addr': ip_address,
            'vnp_create_date': date.strftime('%Y%m%d%H%M%S'),
        }
        
        query_string = self._generate_query_string_vnpay_token(payload)
        payload['vnp_secure_hash'] = self._hmacsha512_token(query_string)
        return payload

    def validate_token_response(self, query):
        """Validate VNPay Token response."""
        vnp_SecureHash = query.get('vnp_SecureHash', '')
        # Remove hash params
        if 'vnp_SecureHash' in query.keys():
            query.pop('vnp_SecureHash')
        if 'vnp_SecureHashType' in query.keys():
            query.pop('vnp_SecureHashType')
        if 'vnp_BankTranNo' in query.keys() and query.get('vnp_BankTranNo') == '':
            query.pop('vnp_BankTranNo')
        query_string = self._generate_query_string_vnpay_token(query)
        return vnp_SecureHash == self._hmacsha512_token(query_string)

    def _hmacsha512_token(self, data):
        """Generate HMAC SHA512 hash for VNPay Token."""
        secret_key = self.search([('code', '=', 'vnpay_token')], limit=1).vnpay_hash_secret_key  # Sử dụng chung field từ payment_vnpay
        byteKey = secret_key.encode('utf-8')
        byteData = data.encode('utf-8')
        return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()

    def _vnpay_token_make_request(self, endpoint, payload=None, method='POST'):
        """Make a request to VNPay Token API."""
        self.ensure_one()
        
        url = self.vnpay_api_url  # Sử dụng chung field từ payment_vnpay
        headers = {
            'Content-Type': 'application/json',
        }
        
        try:
            if method == 'POST':
                response = requests.post(url, json=payload, headers=headers, timeout=60)
            else:
                response = requests.get(url, params=payload, headers=headers, timeout=60)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach VNPay Token endpoint at %s", url)
            raise ValidationError(_("VNPay Token: Could not establish the connection to the API."))
        except requests.exceptions.HTTPError:
            _logger.exception("invalid VNPay Token API request at %s with data %s", url, payload)
            raise ValidationError(_("VNPay Token: The communication with the API failed."))
