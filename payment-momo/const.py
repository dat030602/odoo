# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
_logger = logging.getLogger(__name__)


class PAYMENT_CONFIG:
    def __init__(self):
        self.PAYMENT_RETURN_URL = '/payment/momo/payment-return'
        self.PAYMENT_IPN_URL = "/payment/momo/ipnurl"
        self.PAYMENT_PAYMENT_URL = "https://test-payment.momo.vn/v2/gateway/api/create"
        self.PAYMENT_PAYMENT_URL_CHECK_TRANSACTION = "https://test-payment.momo.vn/v2/gateway/api/query"
        

