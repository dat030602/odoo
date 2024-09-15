import logging
import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
import socket
import requests
import uuid
from werkzeug import urls
from odoo.addons.payment_vnpay.const import CONFIG

_logger = logging.getLogger(__name__)
config = CONFIG()

class payment:
    requestData = {}
    responseData = {}

    def get_hashValue_payment(self, query, secret_key):
        queryString = self.generate_query_string_payment(query)
        hashValue = self.__hmacsha512(secret_key, queryString)
        return hashValue

    def generate_query_string_payment(self, query):
        inputData = json.loads(json.dumps(query, sort_keys=True))
        keys = inputData.keys()
        queryString = ''
        seq = 0
        for key in keys:
            if str(key).startswith('vnp_') and str(key) != 'vnp_SecureHash':
                if seq == 1:
                    queryString = queryString + "&" + key + '=' + urllib.parse.quote_plus(str(inputData[key]))
                else:
                    seq = 1
                    queryString = key + '=' + urllib.parse.quote_plus(str(inputData[key]))
        return queryString

    def generate_url_payment(self, params, secret_key):
        queryString = self.generate_query_string_payment(params)
        hashValue = self.__hmacsha512(secret_key, queryString)
        return config.PAYMENT_URL + "?" + queryString + '&vnp_SecureHash=' + hashValue

    def render_payload(self, base_url, lang, amount, order_id=''):
        if lang == 'en_US':
            vnp_Locale = 'en'
        else:
            vnp_Locale = 'vn'
        if amount:
            amount = int(amount) * 100
        date = datetime.now().astimezone(timezone(timedelta(hours=7)))
        if order_id == '':
            uuidCode = 'HD' + str(uuid.uuid4().int & (1 << 64)-1)
        else:
            uuidCode = order_id
        payload = {
            'vnp_Version': config.VERSION,
            'vnp_Command': 'pay',
            'vnp_TmnCode': 'tmncode',
            'vnp_Amount': amount,
            'vnp_CurrCode': config.CURRCODE,
            'vnp_TxnRef': uuidCode,
            'vnp_OrderInfo': "Thanh toan don hang: " + uuidCode + " | "+ date.strftime('%Y-%m-%d %H:%M:%S'),
            'vnp_OrderType': 'billpayment',
            'vnp_Locale': vnp_Locale,
            'vnp_CreateDate': date.strftime('%Y%m%d%H%M%S'),
            'vnp_ExpireDate': (date + timedelta(minutes=5)).strftime('%Y%m%d%H%M%S'),
            'vnp_IpAddr': socket.gethostbyname(socket.gethostname()),
            'vnp_ReturnUrl': urls.url_join(base_url, config.RETURN_URL),
            'vnp_SecureHash': '',
        }
        return payload

    def validate_response(self, secret_key, query):
        vnp_SecureHash = query['vnp_SecureHash']
        # Remove hash params
        if 'vnp_SecureHash' in query.keys():
            query.pop('vnp_SecureHash')
        if 'vnp_SecureHashType' in query.keys():
            query.pop('vnp_SecureHashType')
        if 'vnp_BankTranNo' in query.keys() and query.get('vnp_BankTranNo') == '':
            query.pop('vnp_BankTranNo')
        hashValue = self.get_hashValue_payment(query, secret_key)
        return vnp_SecureHash == hashValue

    @staticmethod
    def __hmacsha512(key, data):
        byteKey = key.encode('utf-8')
        byteData = data.encode('utf-8')
        return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()
