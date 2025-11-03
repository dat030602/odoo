# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
from urllib.parse import urlparse, parse_qs
from werkzeug.utils import redirect

from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class VNPayTokenController(http.Controller):
    """Controller for handling VNPay Token payment notifications and returns."""

    # VNPay Token response code mapping
    RESPONSE_CODE_MAPPING = {
        '00': 'paid',      # Successful payment
        '01': 'pending',   # Payment pending
        '02': 'failed',    # Payment failed
        '03': 'failed',    # Payment failed
        '04': 'expired',   # Payment expired
        '24': 'canceled',  # Payment canceled
    }

    @http.route('/payment/vnpay_token/token-return/', type='http', auth='public', csrf=False)
    def vnpay_token_return(self):
        """Handle VNPay Token return callback."""
        try:
            # Extract and validate parameters from URL
            params = self._extract_url_parameters()
            if not params or not params.get('vnp_txn_ref'):
                _logger.error("VNPay Token: Missing required parameters in token return")
                return self._redirect_to_payment_status('')

            # Get VNPay Token provider
            provider = self._get_vnpay_token_provider()
            if not provider:
                _logger.error("VNPay Token: Provider not found")
                return self._redirect_to_payment_status('')

            # Determine payment status
            status = self._determine_payment_status(params, provider)
            
            # Handle transaction notification
            self._handle_transaction_notification(params['vnp_txn_ref'], status, params)
            
            return self._redirect_to_payment_status(status)

        except (ValueError, TypeError) as e:
            _logger.error("VNPay Token: Invalid parameter format - %s", str(e))
            return self._redirect_to_payment_status('')
        except Exception as e:
            _logger.error("VNPay Token: Payment processing error - %s", str(e))
            return self._redirect_to_payment_status('')

    @http.route('/payment/vnpay_token/token-cancel/', type='http', auth='public', csrf=False)
    def vnpay_token_cancel(self):
        """Handle VNPay Token cancel callback."""
        try:
            # Extract parameters from URL
            params = self._extract_url_parameters()
            if not params or not params.get('vnp_txn_ref'):
                _logger.error("VNPay Token: Missing required parameters in token cancel")
                return self._redirect_to_payment_status('canceled')

            # Handle transaction notification as canceled
            self._handle_transaction_notification(params['vnp_txn_ref'], 'canceled', params)
            
            return self._redirect_to_payment_status('canceled')

        except Exception as e:
            _logger.error("VNPay Token: Cancel processing error - %s", str(e))
            return self._redirect_to_payment_status('canceled')

    @http.route('/payment/vnpay_token/token-webhook/', type='http', auth='public', csrf=False, methods=['POST'])
    def vnpay_token_webhook(self):
        """Handle VNPay Token webhook notifications."""
        try:
            # Extract parameters from POST data
            params = request.httprequest.form.to_dict()
            if not params or not params.get('vnp_txn_ref'):
                _logger.error("VNPay Token: Missing required parameters in webhook")
                return "Missing parameters", 400

            # Get VNPay Token provider
            provider = self._get_vnpay_token_provider()
            if not provider:
                _logger.error("VNPay Token: Provider not found in webhook")
                return "Provider not found", 400

            # Validate webhook signature
            if not provider.validate_token_response(params):
                _logger.warning("VNPay Token: Webhook validation failed for transaction %s", params.get('vnp_txn_ref', ''))
                return "Invalid signature", 400

            # Determine payment status
            status = self._determine_payment_status(params, provider)
            
            # Handle transaction notification
            self._handle_transaction_notification(params['vnp_txn_ref'], status, params)
            
            return "OK", 200

        except Exception as e:
            _logger.error("VNPay Token: Webhook processing error - %s", str(e))
            return "Internal error", 500

    @http.route('/payment/vnpay_token/get-tokens/', type='http', auth='public', csrf=False, methods=['GET'])
    def vnpay_token_get_tokens(self):
        """Get saved tokens for the current user."""
        try:
            # Get current user
            if request.env.user._is_public():
                return self._json_response({'error': 'User not authenticated'}, 401)

            partner_id = request.env.user.partner_id.id
            
            # Get VNPay Token provider
            provider = self._get_vnpay_token_provider()
            if not provider:
                return self._json_response({'error': 'VNPay Token provider not found'}, 400)

            # Get tokens for the current partner
            tokens = request.env['payment.token'].sudo().search([
                ('partner_id', '=', partner_id),
                ('provider_id', '=', provider.id),
                ('active', '=', True)
            ])

            # Format token data
            token_data = []
            for token in tokens:
                token_data.append({
                    'id': token.id,
                    'card_number': token.name or '****',
                    'bank_code': getattr(token, 'bank_code', 'Unknown'),
                    'expiry_date': getattr(token, 'expiry_date', ''),
                })

            return self._json_response({
                'success': True,
                'tokens': token_data
            })

        except Exception as e:
            _logger.error("VNPay Token: Get tokens error - %s", str(e))
            return self._json_response({'error': str(e)}, 500)

    @http.route('/payment/vnpay_token/create-token/', type='http', auth='public', csrf=False, methods=['POST'])
    def vnpay_token_create_token(self):
        """Create a VNPay token for the current user."""
        try:
            # Get current user
            if not request.env.user._is_public():
                partner_id = request.env.user.partner_id.id
            else:
                return self._json_response({'error': 'User not authenticated'}, 401)

            # Get VNPay Token provider
            provider = self._get_vnpay_token_provider()
            if not provider:
                return self._json_response({'error': 'VNPay Token provider not found'}, 400)

            # Create token
            token, token_url = request.env['payment.token']._vnpay_token_create_token(
                provider, partner_id
            )

            return self._json_response({
                'success': True,
                'token_id': token.id,
                'token_url': token_url,
                'message': 'Token creation initiated'
            })

        except Exception as e:
            _logger.error("VNPay Token: Token creation error - %s", str(e))
            return self._json_response({'error': str(e)}, 500)

    @http.route('/payment/vnpay_token/delete-token/', type='http', auth='public', csrf=False, methods=['POST'])
    def vnpay_token_delete_token(self):
        """Delete a VNPay token."""
        try:
            # Get token ID from request
            token_id = request.httprequest.form.get('token_id')
            if not token_id:
                return self._json_response({'error': 'Token ID required'}, 400)

            # Get token
            token = request.env['payment.token'].sudo().browse(int(token_id))
            if not token.exists():
                return self._json_response({'error': 'Token not found'}, 404)

            # Check if user owns the token
            if not request.env.user._is_public() and token.partner_id.id != request.env.user.partner_id.id:
                return self._json_response({'error': 'Unauthorized'}, 403)

            # Delete token
            success = token._vnpay_token_delete_token()

            if success:
                return self._json_response({
                    'success': True,
                    'message': 'Token deleted successfully'
                })
            else:
                return self._json_response({'error': 'Failed to delete token'}, 500)

        except Exception as e:
            _logger.error("VNPay Token: Token deletion error - %s", str(e))
            return self._json_response({'error': str(e)}, 500)

    @http.route('/payment/vnpay_token/pay-with-token/', type='http', auth='public', csrf=False, methods=['POST'])
    def vnpay_token_pay_with_token(self):
        """Process payment with VNPay token."""
        try:
            # Get parameters from request
            token_id = request.httprequest.form.get('token_id')
            amount = float(request.httprequest.form.get('amount', 0))
            currency_id = int(request.httprequest.form.get('currency_id', 0))
            transaction_reference = request.httprequest.form.get('transaction_reference')

            if not token_id or not amount or not currency_id:
                return self._json_response({'error': 'Missing required parameters'}, 400)

            # Get token
            token = request.env['payment.token'].sudo().browse(int(token_id))
            if not token.exists():
                return self._json_response({'error': 'Token not found'}, 404)

            # Get currency
            currency = request.env['res.currency'].sudo().browse(currency_id)
            if not currency.exists():
                return self._json_response({'error': 'Currency not found'}, 404)

            # Get provider
            provider = token.provider_id
            if not provider or provider.code != 'vnpay_token':
                return self._json_response({'error': 'Invalid provider'}, 400)

            # Create transaction
            tx, payment_url = request.env['payment.transaction']._vnpay_token_create_transaction(
                provider, token.partner_id.id, amount, currency, token, transaction_reference
            )

            return self._json_response({
                'success': True,
                'transaction_id': tx.id,
                'payment_url': payment_url,
                'message': 'Payment initiated'
            })

        except Exception as e:
            _logger.error("VNPay Token: Payment processing error - %s", str(e))
            return self._json_response({'error': str(e)}, 500)

    def _extract_url_parameters(self):
        """Extract and validate parameters from the request URL."""
        try:
            url = request.httprequest.url
            parsed_url = urlparse(url)
            query_dict = parse_qs(parsed_url.query)
            
            # Extract parameters with validation
            params = {
                'vnp_txn_ref': self._get_first_param(query_dict, 'vnp_txn_ref'),
                'vnp_amount': self._safe_int_conversion(query_dict.get('vnp_amount', ['0'])[0]),
                'vnp_order_info': self._get_first_param(query_dict, 'vnp_order_info'),
                'vnp_transaction_no': self._get_first_param(query_dict, 'vnp_transaction_no'),
                'vnp_response_code': self._get_first_param(query_dict, 'vnp_response_code'),
                'vnp_tmn_code': self._get_first_param(query_dict, 'vnp_tmn_code'),
                'vnp_pay_date': self._get_first_param(query_dict, 'vnp_pay_date'),
                'vnp_bank_code': self._get_first_param(query_dict, 'vnp_bank_code'),
                'vnp_card_type': self._get_first_param(query_dict, 'vnp_card_type'),
                'vnp_bank_tran_no': self._get_first_param(query_dict, 'vnp_bank_tran_no'),
                'vnp_transaction_status': self._get_first_param(query_dict, 'vnp_transaction_status'),
                'vnp_secure_hash': self._get_first_param(query_dict, 'vnp_secure_hash'),
                'vnp_token': self._get_first_param(query_dict, 'vnp_token'),
                'vnp_app_user_id': self._get_first_param(query_dict, 'vnp_app_user_id'),
            }
            
            return params
        except Exception as e:
            _logger.error("VNPay Token: Error extracting URL parameters - %s", str(e))
            return None

    def _get_first_param(self, query_dict, key):
        """Safely get the first parameter value from query dictionary."""
        values = query_dict.get(key, [''])
        return values[0] if values else ''

    def _safe_int_conversion(self, value):
        """Safely convert string to integer."""
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0

    def _get_vnpay_token_provider(self):
        """Get VNPay Token payment provider."""
        try:
            return request.env['payment.provider'].sudo().search([('code', '=', 'vnpay_token')], limit=1)
        except Exception as e:
            _logger.error("VNPay Token: Error getting provider - %s", str(e))
            return None

    def _determine_payment_status(self, params, provider):
        """Determine payment status based on response code and validation."""
        try:
            # Validate response if provider supports it
            if hasattr(provider, 'validate_token_response') and not provider.validate_token_response(params):
                _logger.warning("VNPay Token: Response validation failed for transaction %s", params.get('vnp_txn_ref', ''))
                return ''

            response_code = params.get('vnp_response_code', '')
            return self.RESPONSE_CODE_MAPPING.get(response_code, 'canceled')
            
        except Exception as e:
            _logger.error("VNPay Token: Error determining payment status - %s", str(e))
            return ''

    def _handle_transaction_notification(self, reference, status, params=None):
        """Handle transaction notification data."""
        try:
            # Find transaction by reference
            tx = request.env['payment.transaction'].sudo().search([
                ('reference', '=', reference),
                ('provider_id.code', '=', 'vnpay_token')
            ], limit=1)
            
            if tx:
                # Process notification
                if params:
                    tx._vnpay_token_process_notification(params)
                else:
                    # Handle basic notification
                    request.env['payment.transaction'].sudo()._handle_notification_data(
                        'vnpay_token', 
                        {'reference': reference, 'status': status}
                    )
        except Exception as e:
            _logger.error("VNPay Token: Error handling transaction notification - %s", str(e))

    def _redirect_to_payment_status(self, status):
        """Redirect to payment status page."""
        return redirect('/payment/status')

    def _json_response(self, data, status_code=200):
        """Return JSON response."""
        return request.make_json_response(data, status=status_code)
