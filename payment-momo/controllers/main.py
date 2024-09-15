# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo.http import request
import json
import pprint
from urllib.parse import urlparse, parse_qs
import requests

from werkzeug import urls
from werkzeug.exceptions import Forbidden
from werkzeug.utils import redirect

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.tools import html_escape

from odoo.addons.payment_momo.static.src.py.payment import payment as ServicePayment
from odoo.addons.payment_momo.const import PAYMENT_CONFIG

_logger = logging.getLogger(__name__)

payment_service = ServicePayment()
payment_config = PAYMENT_CONFIG()

class PaymentController(http.Controller):
    

    _payment_status = '/payment/status'
    
    ############

    _payment_generate_url = '/payment/momo/payment-generate-url/'

    @http.route(_payment_generate_url, type='json', auth='public', methods=['POST'], csrf=False)
    def payment_generate_url(self, **data):
        newData = json.dumps(data['payload'])
        clen = len(newData)
        response = requests.post(payment_config.PAYMENT_PAYMENT_URL, data=newData,
                                 headers={'Content-Type': 'application/json', 'Content-Length': str(clen)})
        _logger.info(json.dumps(response.json()))
        return json.dumps(response.json())

    ############

    _payment_progess = payment_config.PAYMENT_RETURN_URL

    @http.route(_payment_progess)
    def payment_return(self):
        url = request.httprequest.url
        parsed_url = urlparse(url)
        query_dict = parse_qs(parsed_url.query)
        trading_code = query_dict['orderId'][0]
        index = trading_code.find("HD")  # Find the index of "HD"
        try:
            keyPayment = request.env['payment.provider'].sudo().search(
                [('code', '=', 'momo')])
            # Extract parameters from query_dict, with default values if not present
            params = {
                'partnerCode': query_dict.get('partnerCode', [''])[0],
                'orderId': trading_code,
                'requestId': query_dict.get('requestId', [''])[0],
                'amount': int(query_dict.get('amount', [0])[0]),
                'orderInfo': query_dict.get('orderInfo', [''])[0],
                'orderType': query_dict.get('orderType', [''])[0],
                'transId': query_dict.get('transId', [''])[0],
                'resultCode': int(query_dict.get('resultCode', [0])[0]),
                'message': query_dict.get('message', [''])[0],
                'payType': query_dict.get('payType', [''])[0],
                'responseTime': int(query_dict.get('responseTime', [0])[0]),
                'extraData': query_dict.get('extraData', [''])[0],
                'signature': query_dict.get('signature', [''])[0],
            }
            status = ''
            if payment_service.validate_response(keyPayment['momo_secret_key'], params, keyPayment['momo_access_key']):
                if params['resultCode'] == 0:
                    status = 'paid'
                elif params['resultCode'] == 1000:
                    status = 'pending'
                elif params['resultCode'] == 1005:
                    status = 'expired'
                elif params['resultCode'] == 1003 or params['resultCode'] == 1017:
                    status = 'canceled'
                else:
                    status = 'failed'
            else:
                status = ''
            if index != -1:
                trading_code = trading_code[:index]
            request.env['payment.transaction'].sudo()._handle_notification_data('momo', {'reference': trading_code, 'status': status})
            return redirect(self._payment_status)
        except:
            _logger.error("Lỗi thanh toán")
            status = ''
            if index != -1:
                trading_code = trading_code[:index]
            request.env['payment.transaction'].sudo()._handle_notification_data('momo', {'reference': trading_code, 'status': status})
            return redirect(self._payment_status)
    
    