# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import urllib.parse
import datetime
import uuid
import socket
import hmac
import hashlib
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('vnpay', "VNPay")], ondelete={'vnpay': 'set default'})
    vnpay_tmn_code = fields.Char(string="TMN Code", help="The key solely used to identify the account with VNPay", required_if_provider='vnpay')
    vnpay_hash_secret_key = fields.Char(string="Hash Secret Key", required_if_provider='vnpay', groups='base.group_system')

    # VNPay Configuration Constants
    vnpay_return_url = fields.Char(string="Return URL", default='/payment/vnpay/payment-return/')
    vnpay_webhook_url = fields.Char(string="Webhook URL", default='/payment/vnpay/webhook/')
    vnpay_payment_url = fields.Char(string="Payment URL", default="https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
    vnpay_api_url = fields.Char(string="API URL", default="https://sandbox.vnpayment.vn/merchant_webapi/api/transaction")
    vnpay_version = fields.Char(string="Version", default="2.1.0")
    vnpay_currency_code = fields.Char(string="Currency Code", default="VND")

    # === COMPUTE METHODS ===#

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        res = super(PaymentProvider, self)._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'vnpay').show_credentials_page = True
        return res

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        res = super(PaymentProvider, self)._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'vnpay').update({
            'support_express_checkout': False,
            'support_manual_capture': False,
            'support_tokenization': False,
            'support_refund': 'full_only',
        })
        return res

    @api.onchange('state')
    def _onchange_vnpay_state(self):
        """Update URLs based on state selection."""
        if self.code == 'vnpay':
            if self.state == 'test':
                self.vnpay_payment_url = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
                self.vnpay_api_url = "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction"
            elif self.state == 'enabled':
                self.vnpay_payment_url = "https://vnpayment.vn/paymentv2/vpcpay.html"
                self.vnpay_api_url = "https://vnpayment.vn/merchant_webapi/api/transaction"

    # === CONSTRAINT METHODS ===#

    @api.constrains('state', 'vnpay_tmn_code', 'vnpay_hash_secret_key')
    def _check_state_of_connected_account_is_never_test(self):
        """ Check that the provider of a connected account can never been set to 'test'.

        This constraint is defined in the present module to allow the export of the translation
        string of the `ValidationError` should it be raised by modules that would fully implement
        VNPay Connect.

        Additionally, the field `state` is used as a trigger for this constraint to allow those
        modules to indirectly trigger it when writing on custom fields. Indeed, by always writing on
        `state` together with writing on those custom fields, the constraint would be triggered.

        :return: None
        :raise ValidationError: If the provider of a connected account is set in state 'test'.
        """
        if self.filtered(lambda p: p.code == 'vnpay' and p.state in ('test', 'enabled')):
            if self.vnpay_tmn_code == '' or self.vnpay_hash_secret_key == '':
                raise UserError(_("User must enter the TMN code and Hash Secret Key."))

    def _generate_query_string_vnpay(self, query):
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

    def _generate_url_vnpay(self, params):
        provider = self.search([('code', '=', 'vnpay')], limit=1)
        query_string = self._generate_query_string_vnpay(params)
        return provider.vnpay_payment_url + "?" + query_string

    def _prepare_payload_vnpay(self, amount, transaction_reference=None):
        provider = self.search([('code', '=', 'vnpay')], limit=1)
        ip_address = self.env['ir.config_parameter'].sudo().get_param('payment_vnpay.ip_address')
        base_url = self.get_base_url()
        vnp_Locale = 'en' if self.env.lang == 'en_US' else 'vn'
        if amount:
            amount = int(amount) * 100
        date = datetime.datetime.now().astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        
        # Use provided transaction reference or generate one
        if transaction_reference:
            txn_ref = transaction_reference
        else:
            txn_ref = str(uuid.uuid4().hex[:16])
        
        # Get order type from company settings
        company = self.env.company
        order_type = company.vnp_order_type or '250000'  # Default to 'Thanh toán hóa đơn'
            
        payload = {
            'vnp_Version': provider.vnpay_version,
            'vnp_Command': 'pay',
            'vnp_TmnCode': provider.vnpay_tmn_code,
            'vnp_Amount': amount,
            'vnp_CurrCode': provider.vnpay_currency_code,
            'vnp_TxnRef': txn_ref,
            'vnp_OrderInfo': f"Payment for order: {txn_ref} | {date.strftime('%Y-%m-%d %H:%M:%S')}",
            'vnp_OrderType': order_type,
            'vnp_Locale': vnp_Locale,
            'vnp_CreateDate': date.strftime('%Y%m%d%H%M%S'),
            'vnp_ExpireDate': (date + datetime.timedelta(minutes=15)).strftime('%Y%m%d%H%M%S'),
            'vnp_IpAddr': ip_address,
            'vnp_BankCode': 'VNPAYQR',
            'vnp_ReturnUrl': urllib.parse.urljoin(base_url, provider.vnpay_return_url),
        }
        
        # Add bank code if specified
        query_string = self._generate_query_string_vnpay(payload)
        payload['vnp_SecureHash'] = self._hmacsha512(query_string)
        return payload

    def validate_response(self, query):
        vnp_SecureHash = query['vnp_SecureHash']
        # Remove hash params
        if 'vnp_SecureHash' in query.keys():
            query.pop('vnp_SecureHash')
        if 'vnp_SecureHashType' in query.keys():
            query.pop('vnp_SecureHashType')
        if 'vnp_BankTranNo' in query.keys() and query.get('vnp_BankTranNo') == '':
            query.pop('vnp_BankTranNo')
        query_string = self._generate_query_string_vnpay(query)
        return vnp_SecureHash == self._hmacsha512(query_string)

    def _hmacsha512(self, data):
        secret_key = self.search([('code', '=', 'vnpay')], limit=1).vnpay_hash_secret_key
        byteKey = secret_key.encode('utf-8')
        byteData = data.encode('utf-8')
        return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()


