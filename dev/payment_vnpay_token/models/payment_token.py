# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PaymentToken(models.Model):
    _inherit = 'payment.token'

    # VNPay Token specific fields
    vnpay_token = fields.Char(
        string="VNPay Token", 
        readonly=True,
        help="The VNPay token returned by the payment provider"
    )
    vnpay_card_number = fields.Char(
        string="Card Number (Masked)", 
        readonly=True,
        help="The masked card number returned by VNPay"
    )
    vnpay_bank_code = fields.Char(
        string="Bank Code", 
        readonly=True,
        help="The bank code associated with the token"
    )
    vnpay_card_type = fields.Selection([
        ('01', 'Nội địa'),
        ('02', 'Quốc tế')
    ], string="Card Type", readonly=True)
    vnpay_token_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deleted', 'Deleted')
    ], string="Token Status", default='active', readonly=True)

    def _vnpay_token_create_token(self, provider, partner_id, transaction_reference=None):
        """Create a VNPay token for the given partner.
        
        :param recordset provider: The VNPay Token provider
        :param int partner_id: The partner ID
        :param str transaction_reference: Optional transaction reference
        :return: The created token
        :rtype: recordset of `payment.token`
        """
        self.ensure_one()
        
        # Prepare token creation payload
        payload = provider._prepare_token_create_payload(partner_id, transaction_reference)
        
        # Generate token creation URL
        token_url = provider._generate_url_vnpay_token(payload, 'create')
        
        _logger.info("VNPay Token creation URL: %s", token_url)
        
        # Create token record (will be updated after VNPay callback)
        token = self.create({
            'provider_id': provider.id,
            'partner_id': partner_id,
            'provider_ref': '',  # Will be set after VNPay callback
            'vnpay_token_status': 'active',
        })
        
        return token, token_url

    def _vnpay_token_update_from_response(self, response_data):
        """Update token with VNPay response data.
        
        :param dict response_data: The response data from VNPay
        :return: None
        """
        self.ensure_one()
        
        vnp_token = response_data.get('vnp_token')
        vnp_card_number = response_data.get('vnp_card_number')
        vnp_bank_code = response_data.get('vnp_bank_code')
        vnp_card_type = response_data.get('vnp_card_type')
        vnp_response_code = response_data.get('vnp_response_code')
        
        if vnp_response_code == '00' and vnp_token:
            # Token creation successful
            self.write({
                'provider_ref': vnp_token,
                'vnpay_token': vnp_token,
                'vnpay_card_number': vnp_card_number,
                'vnpay_bank_code': vnp_bank_code,
                'vnpay_card_type': vnp_card_type,
                'vnpay_token_status': 'active',
            })
            _logger.info("VNPay Token created successfully: %s", vnp_token)
        else:
            # Token creation failed
            self.write({
                'vnpay_token_status': 'inactive',
            })
            _logger.warning("VNPay Token creation failed with response code: %s", vnp_response_code)

    def _vnpay_token_delete_token(self):
        """Delete VNPay token.
        
        :return: bool: True if deletion was successful
        """
        self.ensure_one()
        
        if not self.provider_ref:
            _logger.warning("No VNPay token to delete for token ID: %s", self.id)
            return False
            
        try:
            # Prepare token deletion payload
            payload = self.provider_id._prepare_token_delete_payload(self)
            
            # Make API request to delete token
            response = self.provider_id._vnpay_token_make_request('delete', payload)
            
            _logger.info("VNPay Token deletion response: %s", pprint.pformat(response))
            
            # Update token status
            self.write({
                'vnpay_token_status': 'deleted',
            })
            
            return True
            
        except Exception as e:
            _logger.error("Failed to delete VNPay token: %s", str(e))
            return False

    def _vnpay_token_validate_token(self):
        """Validate VNPay token status.
        
        :return: bool: True if token is valid
        """
        self.ensure_one()
        
        if not self.provider_ref or self.vnpay_token_status != 'active':
            return False
            
        # In a real implementation, you might want to make an API call to VNPay
        # to validate the token status. For now, we just check local status.
        return True

    def _vnpay_token_get_payment_url(self, amount, transaction_reference=None):
        """Get payment URL for token-based payment.
        
        :param float amount: The payment amount
        :param str transaction_reference: Optional transaction reference
        :return: str: The payment URL
        """
        self.ensure_one()
        
        if not self._vnpay_token_validate_token():
            raise ValidationError(_("Invalid or expired VNPay token"))
            
        # Prepare token payment payload
        payload = self.provider_id._prepare_token_pay_payload(self, amount, transaction_reference)
        
        # Generate payment URL
        payment_url = self.provider_id._generate_url_vnpay_token(payload, 'pay')
        
        return payment_url

    def action_vnpay_token_delete(self):
        """Action to delete VNPay token."""
        self.ensure_one()
        
        if self._vnpay_token_delete_token():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("VNPay token deleted successfully"),
                    'type': 'success',
                },
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Failed to delete VNPay token"),
                    'type': 'danger',
                },
            }
