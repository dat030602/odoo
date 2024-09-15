# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
_logger = logging.getLogger(__name__)


class CONFIG:
    def __init__(self):
        self.RETURN_URL = '/payment/vnpay/payment-return/'
        self.WEBHOOK_URL = '/payment/vnpay/webhook/'
        self.PAYMENT_URL = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
        self.API_URL = "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction"
        self.VERSION = "2.1.0"
        self.CURRCODE = "VND"