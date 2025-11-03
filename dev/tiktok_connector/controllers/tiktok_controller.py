from odoo import http, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class TikTokController(http.Controller):

    @http.route('/marketplace/tiktok/auth_callback', type='http', auth='public', methods=['GET'], csrf=False)
    def auth_callback(self, **kwargs):
        """
        Handle TikTok authentication callback
        Expected parameters:
        - code: Authorization code from TikTok
        - shop_id: Shop ID from TikTok
        - state: Optional state parameter
        """
        try:
            # Get parameters from callback
            code = kwargs.get('code')
            shop_id = kwargs.get('shop_id')
            state = kwargs.get('state')
            
            _logger.info("TikTok callback received - code: %s, shop_id: %s, state: %s", code, shop_id, state)
            
            if not code or not shop_id:
                _logger.error("Missing required parameters: code=%s, shop_id=%s", code, shop_id)
                return request.render('tiktok_connector.auth_error', {
                    'error_message': _('Missing required parameters from TikTok callback')
                })
            
            # Get the TikTok connector configuration
            connector = request.env['tiktok.connector'].search([], limit=1)
            if not connector:
                _logger.error("No TikTok connector configuration found")
                return request.render('tiktok_connector.auth_error', {
                    'error_message': _('No TikTok connector configuration found')
                })
            
            # Update connector with the authorization code and shop ID
            connector.write({
                'access_token': code,
                'tiktok_shop_id': shop_id
            })
            
            _logger.info("TikTok connector updated with code and shop_id")
            
            return request.render('tiktok_connector.auth_success', {
                'message': _('TikTok authentication successful! You can now close this window and return to Odoo.'),
                'shop_id': shop_id
            })
            
        except Exception as e:
            _logger.error("Error in TikTok auth callback: %s", str(e))
            return request.render('tiktok_connector.auth_error', {
                'error_message': _('An error occurred during TikTok authentication: %s') % str(e)
            })

    @http.route('/marketplace/tiktok/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def webhook(self, **kwargs):
        """
        Handle TikTok webhook notifications
        """
        try:
            # Get the raw request data
            data = request.httprequest.get_data()
            _logger.info("TikTok webhook received: %s", data)
            
            # Process webhook data here
            # This would typically involve parsing the webhook payload
            # and updating orders, products, etc. based on the notification type
            
            return "OK"
            
        except Exception as e:
            _logger.error("Error processing TikTok webhook: %s", str(e))
            return "ERROR"
