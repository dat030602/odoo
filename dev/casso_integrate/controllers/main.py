# -*- coding: utf-8 -*-
import datetime
from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)

class CassoWebhook(http.Controller):

    @http.route('/webhook/casso', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_casso_payment(self, **post):
        # Parse raw JSON body (works for http & json routes)
        try:
            body = json.loads(request.httprequest.data.decode('utf-8'))
        except Exception:
            return {
                "error": 1,
                "message": "Invalid JSON body"
            }

        if body.get('error') != 0:
            return {
                "error": 1,
                "message": "Invalid data format"
            }

        transactions = body.get('data', [])

        payment_model = request.env['account.payment'].sudo()

        for transaction_data in transactions:
            payment_model._create_casso_payment(transaction_data)
        return {
            "error": 0,
            "message": "Ok"
        }


    @http.route('/webhook/casso/authorize', type='json', auth='public', methods=['GET'], csrf=False)
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
