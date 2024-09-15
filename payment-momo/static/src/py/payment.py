import logging
import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime, timedelta, timezone
import socket
import requests
import uuid
import base64
from werkzeug import urls

from odoo.addons.payment_momo.const import PAYMENT_CONFIG

_logger = logging.getLogger(__name__)

payment_config = PAYMENT_CONFIG()


class payment:
    
    def get_orderline(self, base_url, sale_order):
        items = []
        delivery = {}
        user_info = {}
        for item in sale_order:
            for user in item.partner_id:
                user_info['name'] = str(user.display_name)
                user_info['phoneNumber'] = str(user.phone)
                user_info['email'] = str(user.email)
            for address in item.partner_shipping_id:
                delivery['deliveryAddress'] = str(address.street) + ', ' + str(address.city) + ', '
                for state in address.state_id:
                    delivery['deliveryAddress'] = delivery['deliveryAddress'] + str(state.display_name) + ', '
                for country in address.country_id:
                    delivery['deliveryAddress'] = delivery['deliveryAddress'] + str(country.display_name) 
            delivery['deliveryFee'] = str(int(item.amount_delivery))
            for order_line in item.order_line:
                product = {}
                product['quantity'] = int(order_line.product_qty)
                for product_item in order_line.product_id:
                    product['name'] = product_item.display_name
                    product['price'] = int(product_item.list_price)
                    product['totalPrice'] = int(order_line.product_qty) * int(product_item.list_price)
                    # Encode the image bytes to base64
                    product_image_128_bytes = product_item.image_128
                    if product_image_128_bytes != True and product_image_128_bytes != False:
                        base64_encoded_image = base64.b64encode(product_image_128_bytes).decode('utf-8')

                        # Construct the URL
                        image_url = base_url + "/web/image?model=product.product&field=image_128&id={}&unique={}".format(
                            product_item.id, base64_encoded_image)
                        product['imageUrl'] = image_url
                    for tax in product_item.taxes_id:
                        product['amount'] = int(tax.amount)
                        product['amount_type'] = tax.amount_type
                        if tax.amount_type == 'percent':
                            product['taxAmount'] = int(int(product_item.list_price) * int(tax.amount) / 100)
                        elif tax.amount_type == 'division':
                            product['taxAmount'] = int(int(product_item.list_price) * int(tax.amount) / 100)
                        else:
                            product['taxAmount'] = int(tax.amount)
                if ('Delivery' in product['name']) or ('Giao hàng' in product['name']):
                    continue
                else:
                    items.append(product)
        return [items, delivery, user_info]
        
    def get_hashValue_payment(self, query, secret_key, accessKey=None):
        queryString = self.generate_query_string_payment(query, accessKey)
        hashValue = self.__hmacsha512(secret_key, queryString)
        return hashValue

    def generate_query_string_payment(self, query, accessKey):
        inputData = json.loads(json.dumps(query, sort_keys=True))
        keys = inputData.keys()
        queryString = 'accessKey=' + accessKey
        seq = 1
        for key in keys:
            if str(key) == 'accessKey' or \
                str(key) == 'amount' or \
                str(key) == 'extraData' or \
                str(key) == 'ipnUrl' or \
                str(key) == 'orderId' or \
                str(key) == 'orderInfo' or \
                str(key) == 'partnerCode' or \
                str(key) == 'redirectUrl' or \
                str(key) == 'requestId' or \
                str(key) == 'requestType' or \
                str(key) == 'payUrl' or \
                str(key) == 'resultCode' or \
                str(key) == 'message' or \
                str(key) == 'orderType' or \
                str(key) == 'payType' or \
                str(key) == 'responseTime' or \
                str(key) == 'transId':
                if seq == 1:
                    queryString = queryString + "&" + key + '=' + str(inputData[key])
                else:
                    seq = 1
                    queryString = key + '=' + str(inputData[key])
        return queryString


    def generate_url_payment(self, params, secret_key):
        queryString = self.generate_query_string_payment(params)
        hashValue = self.__hmacsha512(secret_key, queryString)
        return payment_config.PAYMENT_PAYMENT_URL + "?" + queryString + '&signature=' + hashValue

    def render_payload(self, amount, key, order_id='', base_url = 'http://localhost:8069', lang = 'vi_VN', items = [], delivery = {}, user_info = {}, isPos=False):
        if lang == 'vi_VN':
            locale = 'vi'
        else:
            locale = 'en'
        if amount:
            amount = int(amount)
        date = datetime.now().astimezone(timezone(timedelta(hours=7)))
        if order_id == '':
            uuidCode = 'HD' + str(uuid.uuid4().int & (1 << 64)-1)
        else:
            uuidCode = order_id
            if "Order " in uuidCode:
                uuidCode = str(uuidCode.replace("Order ", ""))
            if not isPos:
                uuidCode = uuidCode + 'HD' + str(uuid.uuid4().int & (1 << 64)-1)
        partnerCode = key['momo_partner_code']
        accessKey = key['momo_access_key']
        secretKey = key['momo_secret_key']
        partnerName = "Test"
        storeId = "MomoTestStore"
        orderInfo = f"Thanh toan don hang: {uuidCode} | {date.strftime('%Y-%m-%d %H:%M:%S')}"
        redirectUrl = urls.url_join(base_url, payment_config.PAYMENT_RETURN_URL)
        ipnUrl = urls.url_join(base_url, payment_config.PAYMENT_IPN_URL)
        requestId = str(uuid.uuid4())
        requestType = "captureWallet"
        extraData = ""
        payload = {
            'partnerCode': partnerCode,
            'partnerName': partnerName,
            'storeId': storeId,
            'requestId': requestId,
            'amount': amount,
            'orderId': uuidCode,
            'orderInfo': orderInfo,
            'redirectUrl': redirectUrl,
            'ipnUrl': ipnUrl,
            'lang': locale,
            'extraData': extraData,
            'requestType': requestType,
            'referenceId': order_id,
        }
        if items != {}:
            payload['items'] = items
        if delivery != {}:
            payload['delivery'] = delivery
        if user_info != {}:
            payload['userInfo'] = user_info
        payload['signature'] = self.get_hashValue_payment(payload, secretKey, accessKey)
        return payload

    def validate_response(self, secret_key, query, accessKey):
        signature = query['signature']
        # Remove hash params
        if 'signature' in query.keys():
            query.pop('signature')
        hashValue = self.get_hashValue_payment(query, secret_key, accessKey)
        return signature == hashValue

    def render_payload_check_transaction(self, key, order_id='', lang = 'vi_VN'):
        if lang == 'vi_VN':
            locale = 'vi'
        else:
            locale = 'en'
        if order_id == '':
            uuidCode = 'HD' + str(uuid.uuid4().int & (1 << 64)-1)
        else:
            uuidCode = order_id

        if "Order " in uuidCode:
            uuidCode = str(uuidCode.replace("Order ", ""))

        partnerCode = key['momo_partner_code']
        accessKey = key['momo_access_key']
        secretKey = key['momo_secret_key']
        requestId = str(uuid.uuid4())
        payload = {
            'partnerCode': partnerCode,
            'requestId': requestId,
            'orderId': uuidCode,
            'lang': locale,
        }
        payload['signature'] = self.get_hashValue_payment(payload, secretKey, accessKey)
        return payload

    @staticmethod
    def __hmacsha512(key, data):
        byteKey = bytes(key, 'utf-8')
        byteData = bytes(data, 'utf-8')
        h = hmac.new(byteKey, byteData, hashlib.sha256)
        return h.hexdigest()
