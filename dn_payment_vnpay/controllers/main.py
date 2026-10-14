# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)


class VNPayController(http.Controller):

    @http.route('/payment/vnpay/return', type='http', auth='public', methods=['GET'], csrf=False, save_session=False)
    def vnpay_return(self, **data):
        """
        Handle customer redirect from VNPay back to merchant site.
        """
        _logger.info("Received VNPay return redirect with data:\n%s", data)
        if data.get('vnp_TxnRef'):
            request.env['payment.transaction'].sudo()._process('vnpay', data)
        return request.redirect('/payment/status')

    @http.route('/payment/vnpay/ipn', type='http', auth='public', methods=['GET', 'POST'], csrf=False, save_session=False)
    def vnpay_ipn(self, **data):
        """
        Handle server-to-server IPN notification from VNPay.
        Returns JSON response required by VNPay spec:
        {"RspCode": "00", "Message": "Confirm Success"}
        """
        _logger.info("Received VNPay IPN notification with data:\n%s", data)
        
        # Verify transaction
        tx_ref = data.get('vnp_TxnRef')
        if not tx_ref:
            return json.dumps({"RspCode": "01", "Message": "Order Not Found"})
            
        tx_sudo = request.env['payment.transaction'].sudo().search([
            ('reference', '=', tx_ref),
            ('provider_code', '=', 'vnpay')
        ], limit=1)
        
        if not tx_sudo:
            return json.dumps({"RspCode": "01", "Message": "Order Not Found"})
            
        # Verify signature
        verify_res = request.env['connector.execution.engine'].handle_callback(
            'vnpay',
            data,
            hash_style='sorted_query',
            hash_key='vnp_SecureHash',
            secret=tx_sudo.provider_id.vnpay_hash_secret
        )
        
        if not verify_res.get('valid') and tx_sudo.provider_id.vnpay_hash_secret:
            return json.dumps({"RspCode": "97", "Message": "Invalid Checksum"})
            
        # Check amount
        try:
            vnp_amount = int(data.get('vnp_Amount', 0))
            expected_amount = int(tx_sudo.amount * 100)
            if vnp_amount != expected_amount:
                return json.dumps({"RspCode": "04", "Message": "Invalid Amount"})
        except Exception:
            pass

        # Check order already confirmed
        if tx_sudo.state == 'done':
            return json.dumps({"RspCode": "02", "Message": "Order already confirmed"})
            
        try:
            tx_sudo._process('vnpay', data)
            return json.dumps({"RspCode": "00", "Message": "Confirm Success"})
        except Exception as e:
            _logger.error("Error processing VNPay IPN: %s", e)
            return json.dumps({"RspCode": "99", "Message": "Unknown Error"})
