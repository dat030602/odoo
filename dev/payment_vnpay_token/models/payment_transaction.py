                                                                                                                                                                    # Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # VNPay Token specific fields
    vnpay_token_id = fields.Many2one(
        'payment.token',
        string="VNPay Token",
        help="The VNPay token used for this transaction"
    )
    vnpay_token_transaction_no = fields.Char(
        string="VNPay Token Transaction No",
        readonly=True,
        help="The VNPay transaction number for token-based payments"
    )
    vnpay_token_bank_tran_no = fields.Char(
        string="VNPay Token Bank Transaction No",
        readonly=True,
        help="The bank transaction number from VNPay"
    )

    def _vnpay_token_create_transaction(self, provider, partner_id, amount, currency, token, transaction_reference=None):
        """Create a VNPay token transaction.
        
        :param recordset provider: The VNPay Token provider
        :param int partner_id: The partner ID
        :param float amount: The transaction amount
        :param recordset currency: The currency
        :param recordset token: The VNPay token
        :param str transaction_reference: Optional transaction reference
        :return: The created transaction
        :rtype: recordset of `payment.transaction`
        """
        # Create transaction record
        tx = self.create({
            'provider_id': provider.id,
            'partner_id': partner_id,
            'amount': amount,
            'currency_id': currency.id,
            'reference': transaction_reference or self._get_next_reference(),
            'operation': 'online_redirect',
            'state': 'draft',
            'vnpay_token_id': token.id,
        })
        
        # Get payment URL
        payment_url = token._vnpay_token_get_payment_url(amount, tx.reference)
        
        _logger.info("VNPay Token payment URL: %s", payment_url)
        
        return tx, payment_url

    def _vnpay_token_handle_notification_data(self, notification_data):
        """Handle VNPay token notification data.
        
        :param dict notification_data: The notification data from VNPay
        :return: None
        """
        self.ensure_one()
        
        _logger.info("VNPay Token notification data: %s", pprint.pformat(notification_data))
        
        # Extract VNPay response data
        vnp_response_code = notification_data.get('vnp_response_code', '')
        vnp_transaction_no = notification_data.get('vnp_transaction_no', '')
        vnp_bank_tran_no = notification_data.get('vnp_bank_tran_no', '')
        vnp_transaction_status = notification_data.get('vnp_transaction_status', '')
        vnp_amount = notification_data.get('vnp_amount', 0)
        
        # Update transaction with VNPay data
        self.write({
            'vnpay_token_transaction_no': vnp_transaction_no,
            'vnpay_token_bank_tran_no': vnp_bank_tran_no,
        })
        
        # Determine transaction status based on VNPay response
        if vnp_response_code == '00' and vnp_transaction_status == '00':
            # Payment successful
            self._set_done()
            _logger.info("VNPay Token payment successful for transaction %s", self.reference)
        elif vnp_response_code == '00' and vnp_transaction_status == '01':
            # Payment pending
            self._set_pending()
            _logger.info("VNPay Token payment pending for transaction %s", self.reference)
        else:
            # Payment failed
            self._set_canceled()
            _logger.warning("VNPay Token payment failed for transaction %s with response code %s", 
                          self.reference, vnp_response_code)

    def _vnpay_token_validate_notification_data(self, notification_data):
        """Validate VNPay token notification data.
        
        :param dict notification_data: The notification data from VNPay
        :return: bool: True if notification is valid
        """
        self.ensure_one()
        
        # Validate using provider's validation method
        if hasattr(self.provider_id, 'validate_token_response'):
            return self.provider_id.validate_token_response(notification_data)
        
        return True

    def _vnpay_token_process_notification(self, notification_data):
        """Process VNPay token notification.
        
        :param dict notification_data: The notification data from VNPay
        :return: None
        """
        self.ensure_one()
        
        # Validate notification
        if not self._vnpay_token_validate_notification_data(notification_data):
            _logger.warning("Invalid VNPay Token notification for transaction %s", self.reference)
            return
        
        # Handle notification data
        self._vnpay_token_handle_notification_data(notification_data)

    def _vnpay_token_create_refund_transaction(self, amount_to_refund):
        """Create a refund transaction for VNPay token payment.
        
        :param float amount_to_refund: The amount to refund
        :return: The created refund transaction
        :rtype: recordset of `payment.transaction`
        """
        self.ensure_one()
        
        # Create refund transaction
        refund_tx = self._create_child_transaction(amount_to_refund, is_refund=True)
        
        # For VNPay Token, refunds are typically processed through the original payment method
        # This would require additional API integration with VNPay
        _logger.info("VNPay Token refund transaction created: %s", refund_tx.reference)
        
        return refund_tx

    def _vnpay_token_get_supported_currencies(self):
        """Get supported currencies for VNPay Token.
        
        :return: list: List of supported currency codes
        """
        return ['VND']  # VNPay primarily supports VND

    def _vnpay_token_get_supported_countries(self):
        """Get supported countries for VNPay Token.
        
        :return: list: List of supported country codes
        """
        return ['VN']  # VNPay is primarily for Vietnam
