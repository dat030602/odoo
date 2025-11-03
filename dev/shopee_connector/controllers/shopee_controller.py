from odoo import http, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class ShopeeController(http.Controller):

    @http.route('/marketplace/shopee/auth_callback', type='http', auth='public', methods=['GET'], csrf=False)
    def auth_callback(self, **kwargs):
        """
        Handle Shopee authentication callback
        Expected parameters:
        - code: Authorization code from Shopee
        - shop_id: Shop ID from Shopee
        - state: Optional state parameter
        """
        try:
            # Get parameters from callback
            code = kwargs.get('code')
            shop_id = kwargs.get('shop_id')
            state = kwargs.get('state')
            
            _logger.info("Shopee callback received - code: %s, shop_id: %s, state: %s", code, shop_id, state)
            
            if not code or not shop_id:
                _logger.error("Missing required parameters: code=%s, shop_id=%s", code, shop_id)
                return request.render('ccv_marketplace_connector.auth_error', {
                    'error_message': _('Missing required parameters from Shopee callback')
                })
            
            # Get marketplace config
            config = request.env['shopee.connector'].search([], limit=1)
            if not config:
                _logger.error("No Shopee configuration found")
                return request.render('ccv_marketplace_connector.auth_error', {
                    'error_message': _('No Shopee configuration found')
                })
            
            # Update config with received parameters
            config.write({
                'access_token': code,
                'shopee_shop_id': shop_id,
            })
            
            # Log success
            _logger.info("Successfully received Shopee authorization code and shop_id")

            config.action_get_token()
            config.action_get_shop_info()
            config.action_active()
            
            # Return success page
            return request.render('ccv_marketplace_connector.auth_success', {
                'message': _('Shopee authentication successful!'),
                'shop_id': shop_id,
                'next_step': _('Please go to Marketplace Configuration to complete the token exchange.')
            })
            
        except Exception as e:
            _logger.error("Error in Shopee auth callback: %s", str(e))
            return request.render('ccv_marketplace_connector.auth_error', {
                'error_message': _('An error occurred during authentication: %s') % str(e)
            })
