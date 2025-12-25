# -*- coding: utf-8 -*-
import datetime
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class CassoWebhook(http.Controller):

    @http.route('/webhook/casso', type='json', auth='none', methods=['POST'], csrf=False)
    def receive_casso_payment(self, **post):
        # 1. Get data from Casso (Odoo automatically parses JSON body)
        body = request.jsonrequest
        
        # Check basic data validity
        if not body or body.get('error') != 0:
            return {"error": 1, "message": "Invalid data format"}

        # Casso v2 returns a list of transactions in the 'data' field
        
        transactions = body.get('data', [])
        # 2. Get account.payment model with sudo rights
        payment_model = request.env['account.payment'].sudo()

        # 3. Iterate through each transaction and push to your processing function
        for transaction_data in transactions:
            try:
                # Call your existing processing function
                payment_model._create_casso_payment(transaction_data)
                _logger.info(f"Casso: Transaction {transaction_data.get('reference')} has been pushed to processing.")
            except Exception as e:
                _logger.error(f"Casso: Error when processing transaction via _create_casso_payment function: {str(e)}")

        # 4. Return response to Casso
        return {"error": 0, "message": "Ok"}

    @http.route('/webhook/casso/authorize', type='json', auth='none', methods=['GET'], csrf=False)
    def authorize_casso(self):
        casso_config = request.env['casso.config'].sudo().search([], limit=1)
        body = request.jsonrequest
        
        # Check basic data validity
        if not body or body.get('error') != 0:
            return {"error": 1, "message": "Invalid data format"}
        casso_config.write({
            'casso_refresh_token': body.get('refresh_token', False),
            'casso_access_token': body.get('access_token', False),
            'token_expires_at': datetime.datetime.now() + datetime.timedelta(seconds=body.get('expires_in')),
            'status': 'connected',
        })

        return request.env['casso.config'].sudo().action_authorize_token()
