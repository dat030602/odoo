# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import json
import werkzeug
from datetime import datetime, timedelta, timezone
from werkzeug import urls

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo.http import request

from odoo import http

from odoo.addons.payment_vnpay.static.src.py.vnpay import vnpay as ServiceVNPay

_logger = logging.getLogger(__name__)

vnpay_service = ServiceVNPay()


class PosVnpayStackPayment(models.Model):
    _name = 'pos_vnpay.stack_payment'
    _description = 'Pos Vnpay Stack Payment'

    # VNPay
    order_id = fields.Char(string='Order Id')
    status_order = fields.Char(string='Status Order')
    trading_code = fields.Char(string='Trading Code')
    payload = fields.Char(string='Pay load')
    qr_code = fields.Char(string='QR Code')

    @api.model
    def validate_payment(self, value, amount):
        try:
            if amount != None:
                records = request.env['pos_vnpay.stack_payment'].search(
                    [('order_id', '=', value)], limit=1)

                index = 0

                if len(records) > 0:
                    for record in records:
                        if record.status_order == 'done':
                            return True
                    date = datetime.now().astimezone(timezone(timedelta(hours=7)))
                    el = record[index]
                    vnpayCode = request.env['payment.provider'].search(
                        [('code', '=', 'vnpay')])
                    order_id = el['order_id']
                    status_order = el['status_order']
                    payload = json.loads(el['payload'])
                    vnp_Version = payload['vnp_Version']
                    vnp_Command = payload['vnp_Command']
                    vnp_TmnCode = payload['vnp_TmnCode']
                    vnp_Amount = payload['vnp_Amount']
                    vnp_CurrCode = payload['vnp_CurrCode']
                    vnp_TxnRef = payload['vnp_TxnRef']
                    vnp_OrderInfo = payload['vnp_OrderInfo']
                    vnp_OrderType = payload['vnp_OrderType']
                    vnp_Locale = payload['vnp_Locale']
                    vnp_IpAddr = payload['vnp_IpAddr']
                    vnp_ReturnUrl = payload['vnp_ReturnUrl']
                    vnp_CreateDate = (date).strftime('%Y%m%d%H%M%S')
                    vnp_ExpireDate = (date + timedelta(minutes=15)
                                    ).strftime('%Y%m%d%H%M%S')
                    json_payload = {
                        'vnp_Version': vnp_Version,
                        'vnp_Command': vnp_Command,
                        'vnp_TmnCode': vnp_TmnCode,
                        'vnp_Amount': vnp_Amount,
                        'vnp_CurrCode': vnp_CurrCode,
                        'vnp_TxnRef': vnp_TxnRef,
                        'vnp_OrderInfo': vnp_OrderInfo,
                        'vnp_OrderType': vnp_OrderType,
                        'vnp_Locale': vnp_Locale,
                        'vnp_CreateDate': vnp_CreateDate,
                        'vnp_ExpireDate': vnp_ExpireDate,
                        'vnp_IpAddr': vnp_IpAddr,
                        'vnp_ReturnUrl': vnp_ReturnUrl,
                    }
                    json_payload['vnp_SecureHash'] = vnpay_service.get_hashValue_payment(
                        json_payload, vnpayCode.vnpay_hash_secret_key)

                    temp_payload = {'order_id': order_id,
                                    'trading_code': payload['vnp_TxnRef'],
                                    'status_order': status_order,
                                    'payload': json.dumps(json_payload),
                                    'qr_code': 'empty'
                                    }

                    record_to_update = self.env['pos_vnpay.stack_payment'].browse(
                        record[index].id)
                    if record_to_update:
                        record_to_update.write(temp_payload)
                        url = vnpay_service.generate_url_payment(
                            json_payload, vnpayCode.vnpay_hash_secret_key)
                        return url
                    return False
                else:
                    payload = vnpay_service.render_payload(
                        'http://localhost:8069', 'vn', '')

                    vnpayCode = request.env['payment.provider'].search(
                        [('code', '=', 'vnpay')])

                    payload['vnp_Amount'] = int(amount * 24400 * 100)

                    returnURL = payload['vnp_ReturnUrl']

                    arrReturnURL = returnURL.split("/payment/")

                    payload['vnp_ReturnUrl'] = arrReturnURL[0] + \
                        "/payment/pos-" + arrReturnURL[1]

                    for code in vnpayCode:
                        payload['vnp_TmnCode'] = code.vnpay_tmn_code
                        break

                    url = vnpay_service.generate_url_payment(
                        payload, vnpayCode.vnpay_hash_secret_key)

                    date = datetime.now().astimezone(timezone(timedelta(hours=7)))
                    payload['vnp_SecureHash'] = vnpay_service.get_hashValue_payment(
                        payload, vnpayCode.vnpay_hash_secret_key),

                    self.create({
                        'order_id': value,
                        'trading_code': payload['vnp_TxnRef'],
                        'status_order': 'waiting',
                        'payload': json.dumps(payload),
                        'qr_code': 'empty'
                    })

                    return url
            else:
                return False
        except:
            return False

        

    @api.model
    def get_qr_code(self, value, qrcode, isAllowGetQR=False):
        records = request.env['pos_vnpay.stack_payment'].search(
            [('order_id', '=', value)])
        if len(records) > 0:
            el = records[0]
            qr_code = el['qr_code']
            if qr_code == 'empty':
                if qrcode != '':
                    order_id = el['order_id']
                    status_order = el['status_order']
                    vnp_Version = el['vnp_Version']
                    vnp_Command = el['vnp_Command']
                    vnp_TmnCode = el['vnp_TmnCode']
                    vnp_Amount = el['vnp_Amount']
                    vnp_CurrCode = el['vnp_CurrCode']
                    vnp_TxnRef = el['vnp_TxnRef']
                    vnp_OrderInfo = el['vnp_OrderInfo']
                    vnp_OrderType = el['vnp_OrderType']
                    vnp_Locale = el['vnp_Locale']
                    vnp_CreateDate = el['vnp_CreateDate']
                    vnp_ExpireDate = el['vnp_ExpireDate']
                    qr_code = qrcode
                    vnp_IpAddr = el['vnp_IpAddr']
                    vnp_ReturnUrl = el['vnp_ReturnUrl']
                    vnp_SecureHash = el['vnp_SecureHash']
                    detail_order = el['detail_order']
                    temp_payload = {'order_id': order_id,
                                    'status_order': status_order,
                                    'vnp_Version': vnp_Version,
                                    'vnp_Command': vnp_Command,
                                    'vnp_TmnCode': vnp_TmnCode,
                                    'vnp_Amount': vnp_Amount,
                                    'vnp_CurrCode': vnp_CurrCode,
                                    'vnp_TxnRef': vnp_TxnRef,
                                    'vnp_OrderInfo': vnp_OrderInfo,
                                    'vnp_OrderType': vnp_OrderType,
                                    'vnp_Locale': vnp_Locale,
                                    'vnp_CreateDate': vnp_CreateDate,
                                    'vnp_ExpireDate': vnp_ExpireDate,
                                    'vnp_IpAddr': vnp_IpAddr,
                                    'vnp_ReturnUrl': vnp_ReturnUrl,
                                    'vnp_SecureHash': vnp_SecureHash,
                                    'detail_order': detail_order,
                                    'qr_code': qr_code,
                                    }
                    record_to_update = self.env['pos_vnpay.stack_payment'].browse(
                        el.id)
                    record_to_update.write(temp_payload)

                    return {'order_id': record_to_update.order_id}
                return True
            elif isAllowGetQR:
                return qr_code
        return False

    @api.model
    def create(self, values):
        return super(PosVnpayStackPayment, self).create(values)

    # @api.model
    # def write(self, values):
    #     order = request.env['pos_vnpay.stack_payment'].search(
    #         [('order_id', '=', values['order_id'])])
    #     if order:
    #         order.write(values)
    #         return True
    #     return False

    @api.model
    def getValue(self, value):

        orders = request.env['pos_vnpay.stack_payment'].search(
            [('order_id', '=', value)])

        result = []

        for order in orders:
            # Do something with each matching partner record
            result.append({
                'order_id': order.order_id,
                'create_date': order.create_date,
                'expiration_date': order.expiration_date,
                'status_order': order.status_order
            })

        return result

    @api.model
    def delete_record(self, record_id):
        # Find the record by ID
        record = self.env['pos_vnpay.stack_payment'].browse(record_id)
        if record.exists():
            # Use the unlink method to delete the record
            record.unlink()
            return True

        else:
            return False
