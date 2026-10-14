# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from werkzeug import urls
import pprint
import logging

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'vnpay':
            return res

        base_url = self.provider_id.get_base_url()
        return_url = urls.url_join(base_url, '/payment/vnpay/return')
        
        # Build amount in VNPay format (integer without decimals, multiplied by 100)
        vnp_amount = int(self.amount * 100)
        
        # Format now as UTC+7 (VNPay requires Asia/Ho_Chi_Minh timezone: yyyyMMddHHmmss)
        now_dt = fields.Datetime.now()
        create_date_str = now_dt.strftime('%Y%m%d%H%M%S')
        
        extra_params = {
            'vnp_Amount': vnp_amount,
            'vnp_TxnRef': self.reference,
            'vnp_OrderInfo': f"Payment for {self.reference}",
            'vnp_ReturnUrl': return_url,
            'vnp_CreateDate': create_date_str,
            'vnp_IpAddr': '127.0.0.1',
        }
        
        # Use provider fields if set, otherwise fallback to connector settings
        if self.provider_id.vnpay_tmn_code:
            extra_params['vnp_TmnCode'] = self.provider_id.vnpay_tmn_code
        if self.provider_id.vnpay_hash_secret:
            extra_params['hash_secret'] = self.provider_id.vnpay_hash_secret

        env_code = 'production' if self.provider_id.state == 'enabled' else 'sandbox'

        try:
            redirect_url = self.env['connector.execution.engine'].build_redirect_url(
                'vnpay_pay',
                self,
                extra_params=extra_params,
                environment_code=env_code
            )
        except Exception as e:
            _logger.warning("Could not build VNPay redirect URL via connector engine: %s", e)
            redirect_url = f"https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?error={urls.url_quote(str(e))}"

        return {
            'api_url': redirect_url,
        }

    connector_response_log_id = fields.Many2one(
        'connector.response.log',
        string='Connector Response Log',
        readonly=True,
        groups='dn_payment_connector_base.group_connector_user',
        help='Connector log recording the API callback response',
    )
    connector_response_log_body = fields.Text(
        string='Connector Log Content',
        compute='_compute_connector_response_log_body',
        readonly=True,
        help='Raw content of the connector response log',
    )

    @api.depends('connector_response_log_id', 'connector_response_log_id.body')
    def _compute_connector_response_log_body(self):
        for tx in self:
            tx.connector_response_log_body = tx.connector_response_log_id.body or ''

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        if provider_code != 'vnpay':
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get('vnp_TxnRef')

    def _extract_amount_data(self, payment_data):
        if self.provider_code != 'vnpay':
            return super()._extract_amount_data(payment_data)
        vnp_amount = float(payment_data.get('vnp_Amount', 0)) / 100
        return {
            'amount': vnp_amount,
            'currency_code': self.currency_id.name,
        }

    def _apply_updates(self, payment_data):
        super()._apply_updates(payment_data)
        if self.provider_code != 'vnpay':
            return

        import json

        # 1. Create connector response log
        log_vals = {
            'provider_id': self.provider_id.connector_provider_id.id if self.provider_id.connector_provider_id else False,
            'status_code': 200,
            'status_text': f"Callback received (ResponseCode: {payment_data.get('vnp_ResponseCode', 'N/A')})",
            'body': json.dumps(payment_data, indent=2, ensure_ascii=False) if isinstance(payment_data, dict) else str(payment_data),
            'body_type': 'JSON',
            'response_time': fields.Datetime.now(),
        }
        conn_provider = self.provider_id.connector_provider_id
        if conn_provider:
            api_rec = self.env['connector.api'].sudo().search([
                ('provider_id', '=', conn_provider.id),
                ('code', '=', 'vnpay_pay')
            ], limit=1)
            if api_rec:
                log_vals['api_id'] = api_rec.id

        response_log = self.env['connector.response.log'].sudo().create(log_vals)
        self.connector_response_log_id = response_log.id

        # 2. Verification through execution engine
        verify_result = self.env['connector.execution.engine'].handle_callback(
            'vnpay',
            payment_data,
            hash_style='sorted_query',
            hash_key='vnp_SecureHash',
            secret=self.provider_id.vnpay_hash_secret
        )
        
        if not verify_result.get('valid') and self.provider_id.vnpay_hash_secret:
            response_log.sudo().write({
                'status_code': 400,
                'status_text': 'Invalid Signature',
            })
            _logger.error("VNPay: invalid signature for transaction %s", self.reference)
            self._set_error(_("VNPay: The payment signature is invalid."))
            return

        response_code = payment_data.get('vnp_ResponseCode')
        transaction_no = payment_data.get('vnp_TransactionNo')
        if transaction_no:
            self.provider_reference = transaction_no

        if response_code == '00':
            response_log.sudo().write({'status_text': f"Success - Transaction {transaction_no}"})
            self._set_done()
        elif response_code == '24':
            response_log.sudo().write({'status_text': "Canceled by Customer"})
            self._set_canceled()
        else:
            response_log.sudo().write({'status_code': 400, 'status_text': f"Failed - Code {response_code}"})
            self._set_error(_("VNPay: Payment failed with response code %s", response_code))

    def _process_notification_data(self, notification_data):
        """Backward compatibility / test helper."""
        self._apply_updates(notification_data)
