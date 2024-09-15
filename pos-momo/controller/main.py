from odoo import http, _

import logging
import json
import base64
import requests
from urllib.parse import urlparse, parse_qs
from werkzeug.wrappers import Response
from werkzeug.utils import redirect

from odoo.addons.payment_momo.static.src.py.payment import payment as ServicePayment
from odoo.addons.payment_momo.const import PAYMENT_CONFIG

_logger = logging.getLogger(__name__)

payment_service = ServicePayment()
payment_config = PAYMENT_CONFIG()

class PaymentController(http.Controller):

    _payment_pos_generate_url = '/payment/pos/momo/payment-generate-url'

    @http.route(_payment_pos_generate_url, type='json', auth='user', methods=['POST'], csrf=False)
    def payment_pos_generate_url(self, **data):
        base_url = self.get_base_url(http.request.httprequest.url)
        keys = http.request.env['payment.provider'].sudo().search([('code', '=', 'momo')])
        key = {}
        key['momo_partner_code'] = keys['momo_partner_code']
        key['momo_access_key'] = keys['momo_access_key']
        key['momo_public_key'] = keys['momo_public_key']
        key['momo_secret_key'] = keys['momo_secret_key']
        payload = payment_service.render_payload(data['amount'], key, data['reference'], base_url, 'vi_VN', [], {}, {}, True)
        newData = json.dumps(payload)
        clen = len(newData)
        response = requests.post(payment_config.PAYMENT_PAYMENT_URL, data=newData,
                                 headers={'Content-Type': 'application/json', 'Content-Length': str(clen)})
        _logger.info(response.json())
        return json.dumps(response.json())
    
    ##################

    _payment_pos_check_transaction = '/payment/pos/momo/payment-check-transaction'

    @http.route(_payment_pos_check_transaction, type='json', auth='user', methods=['POST'], csrf=False)
    def payment_pos_check_transaction(self, **data):
        keys = http.request.env['payment.provider'].sudo().search([('code', '=', 'momo')])
        key={}
        key['momo_partner_code'] = keys['momo_partner_code']
        key['momo_access_key'] = keys['momo_access_key']
        key['momo_public_key'] = keys['momo_public_key']
        key['momo_secret_key'] = keys['momo_secret_key']
        payload = payment_service.render_payload_check_transaction(key, data['reference'])
        _logger.info(payload)
        newData = json.dumps(payload)
        clen = len(newData)
        response = requests.post(payment_config.PAYMENT_PAYMENT_URL_CHECK_TRANSACTION, data=newData,
                                 headers={'Content-Type': 'application/json', 'Content-Length': str(clen)})
        _logger.info(response.json())
        # if int(response_data["resultCode"]) == 0:
        #     http.request.env['payment.transaction'].sudo()._handle_notification_data('momo',
        #          {'reference': data['orderID'], 'status': "paid"})
        #     return redirect(self._payment_status)
        return json.dumps(response.json())
    
    
    @staticmethod
    def get_base_url(url):
        base_url = requests.compat.urljoin(url, '/')
        return base_url[:-1]

    ##################

    _payment_ipnurl = payment_config.PAYMENT_IPN_URL

    @http.route(_payment_ipnurl, type='http', auth='public', csrf=False, methods=['POST'])
    def payment_ipn(self, **post):
        query_dict = http.request.httprequest.get_json()
        trading_code = query_dict['orderId']
        index = trading_code.find("HD")  # Find the index of "HD"
        try:
            keyPayment = http.request.env['payment.provider'].sudo().search([('code', '=', 'momo')])
            # Extract parameters from query_dict, with default values if not present
            params = {
                'partnerCode': query_dict.get('partnerCode', ''),
                'orderId': trading_code,
                'requestId': query_dict.get('requestId', ''),
                'amount': int(query_dict.get('amount', 0)),
                'orderInfo': query_dict.get('orderInfo', ''),
                'orderType': query_dict.get('orderType', ''),
                'transId': query_dict.get('transId', ''),
                'resultCode': int(query_dict.get('resultCode', 0)),
                'message': query_dict.get('message', ''),
                'payType': query_dict.get('payType', ''),
                'responseTime': int(query_dict.get('responseTime', 0)),
                'extraData': query_dict.get('extraData', ''),
                'signature': query_dict.get('signature', ''),
            }
            status = ''
            if query_dict.get('payType', '') == 'qr' and payment_service.validate_response(keyPayment['momo_secret_key'], params, keyPayment['momo_access_key']):
                if params['resultCode'] == 0:
                    status = 'paid'
                    account_payment_method_lines = http.request.env['account.payment.method.line'].sudo().search([])
                    account_payment_method_line_id = -1
                    for account_payment_method_line in account_payment_method_lines:
                        if 'Momo' in account_payment_method_line['display_name'] or 'Momo' in account_payment_method_line['name']:
                            account_payment_method_line_id = account_payment_method_line['id']
                            break
                    payment_method_lines = http.request.env['pos.payment.method'].sudo().search([])
                    payment_method_line_id = -1
                    for payment_method_line in payment_method_lines:
                        if 'Momo' in payment_method_line['display_name'] or 'Momo' in payment_method_line['name']:
                            payment_method_line_id = payment_method_line['id']
                            break
                    if index != -1:
                        trading_code = trading_code[:(index-1)]
                    pos_order = http.request.env['pos.order'].sudo().search([('pos_reference', '=', 'Order ' + trading_code)], limit=1)
                    account_payment = http.request.env['account.payment'].sudo().create({
                        'amount': abs(int(query_dict.get('amount', 0))),
                        'journal_id': pos_order['sale_journal'].id,
                        'ref': _('Combine %s POS payments from %s', 'Momo', pos_order['pos_reference']),
                        'pos_payment_method_id': payment_method_line_id,
                        'payment_method_line_id': account_payment_method_line_id,
                        'pos_session_id': pos_order['session_id'].id,
                        'company_id': pos_order['company_id'].id,
                        'pos_order_id': pos_order['id'],
                        'cashier': pos_order['session_id'].user_id.id,
                        'partner_id': pos_order['session_id'].company_id.partner_id.id,
                    })
                    pos_order._send_online_payments_notification_via_bus()
                else:
                    status = 'failed'
            else:
                status = ''
            
            return Response(status=204)
        except:
            _logger.error("Lỗi thanh toán")
            if index != -1:
                trading_code = trading_code[:index]
            return Response(status=204)