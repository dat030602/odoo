# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
from urllib.parse import urlparse, parse_qs
import requests

from werkzeug.utils import redirect
from odoo import _, http
from odoo.http import request
from odoo.addons.payment_vnpay.static.src.py.payment import payment as ServicePayment

_logger = logging.getLogger(__name__)
payment_service = ServicePayment()

class VNPayController(http.Controller):
    _payment_status = '/payment/status'

    ############

    _payment_generate_url = '/payment/vnpay/payment-generate-url/'
    @http.route(_payment_generate_url, type='json', auth='public', methods=['POST'], csrf=False)
    def payment_generate_url(self, **data):
        code = request.env['payment.provider'].sudo().search([('code', '=', 'vnpay')])
        data['payload']['vnp_TmnCode'] = code['vnpay_tmn_code']
        url = payment_service.generate_url_payment(
            data['payload'], code['vnpay_hash_secret_key'])
        return json.dumps({"url": url})

    ############

    _payment_progess = '/payment/vnpay/payment-return/'
    @http.route(_payment_progess)
    def payment_return(self):
        url = request.httprequest.url
        parsed_url = urlparse(url)
        query_dict = parse_qs(parsed_url.query)
        trading_code = query_dict.get('vnp_TxnRef', [''])[0]
        params = {'vnp_TxnRef': trading_code,
                    'vnp_Amount': int(query_dict.get('vnp_Amount', [''])[0]),
                    'vnp_OrderInfo': query_dict.get('vnp_OrderInfo', [''])[0],
                    'vnp_TransactionNo': query_dict.get('vnp_TransactionNo', [''])[0],
                    'vnp_ResponseCode': query_dict.get('vnp_ResponseCode', [''])[0],
                    'vnp_TmnCode': query_dict.get('vnp_TmnCode', [''])[0],
                    'vnp_PayDate': query_dict.get('vnp_PayDate', [''])[0],
                    'vnp_BankCode': query_dict.get('vnp_BankCode', [''])[0],
                    'vnp_CardType': query_dict.get('vnp_CardType', [''])[0],
                    'vnp_BankTranNo': query_dict.get('vnp_BankTranNo', [''])[0],
                    'vnp_TransactionStatus': query_dict.get('vnp_TransactionStatus', [''])[0],
                    'vnp_SecureHash': query_dict.get('vnp_SecureHash', [''])[0]}
        try:
            keyPayment = request.env['payment.provider'].sudo().search([('code', '=', 'vnpay')])
            status = ''
            if payment_service.validate_response(keyPayment['vnpay_hash_secret_key'], params):
                if params['vnp_ResponseCode'] == "00":
                    status = 'paid'
                elif params['vnp_ResponseCode'] == "02":
                    status = 'pending'
                elif params['vnp_ResponseCode'] == "04":
                    status = 'expired'
                elif params['vnp_ResponseCode'] == "03":
                    status = 'failed'
                else:
                    status = 'canceled'
            else:
                status = ''
            request.env['payment.transaction'].sudo()._handle_notification_data('vnpay', {'reference': trading_code,'status': status})
            return redirect(self._payment_status)
        except:
            _logger.error("Lỗi thanh toán")
            status = ''
            request.env['payment.transaction'].sudo()._handle_notification_data('vnpay', {'reference': trading_code, 'status': status})
            return redirect(self._payment_status)
