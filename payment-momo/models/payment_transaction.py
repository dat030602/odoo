import logging
import pprint
import base64
from datetime import datetime, timedelta

from werkzeug import urls

from odoo import _, models, api
from odoo.exceptions import ValidationError
from odoo.tools import get_lang

from odoo.addons.payment_momo.static.src.py.payment import payment as ServicePayment

_logger = logging.getLogger(__name__)

payment_service = ServicePayment()

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    
    # Business method

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return Stripe-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'momo':
            return res

        base_url = self.provider_id.get_base_url()
        lang = get_lang(self.env).code
        
        result = payment_service.get_orderline(base_url, self.sale_order_ids)

        keys = self.env['payment.provider'].sudo().search([('code', '=', 'momo')])
        key={}

        key['momo_partner_code'] = keys['momo_partner_code']
        key['momo_access_key'] = keys['momo_access_key']
        key['momo_public_key'] = keys['momo_public_key']
        key['momo_secret_key'] = keys['momo_secret_key']
        
        payload = payment_service.render_payload(self.amount, key, self.reference,
                                                 base_url, lang, result[0], result[1], result[2])

        return {
            'data': {
                'payload': payload,
                'status': "",
            }
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Payment data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'momo' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'momo')]
                         )
        if not tx:
            raise ValidationError(
                "Payment: " + _("No transaction found matching reference %s.", reference))
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Payment data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'momo':
            return

        self.provider_reference = f'momo-{self.reference}'

        payment_status = notification_data.get('status')

        if payment_status == 'pending':
            self._set_pending()
        elif payment_status == 'authorized':
            self._set_authorized()
        elif payment_status == 'paid':
            self._set_done()
        elif payment_status in ['expired', 'canceled', 'failed']:
            self._set_canceled(
                "Payment: " + _("Canceled payment with status: %s", payment_status))
        else:
            _logger.info("received data with invalid payment status (%s) for transaction with reference %s", payment_status, self.reference)
            self._set_error("Payment: " + _("Received data with invalid payment status: %s", payment_status))

    def _send_payment_request(self):
        """ Override of payment to simulate a payment request.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_payment_request()
        if self.provider_code != 'momo':
            return

        notification_data = {
            'reference': self.reference, 'status': 'paid'}
        self._handle_notification_data('momo', notification_data)

    def _send_refund_request(self, **kwargs):
        """ Override of payment to simulate a refund.

        Note: self.ensure_one()

        :param dict kwargs: The keyword arguments.
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request(**kwargs)
        if self.provider_code != 'momo':
            return refund_tx

        notification_data = {
            'reference': refund_tx.reference, 'status': 'done'}
        refund_tx._handle_notification_data('momo', notification_data)

        return refund_tx

    def _send_capture_request(self, amount_to_capture=None):
        """ Override of `payment` to simulate a capture request. """
        child_capture_tx = super()._send_capture_request(
            amount_to_capture=amount_to_capture)
        if self.provider_code != 'momo':
            return child_capture_tx

        tx = child_capture_tx or self
        notification_data = {
            'reference': tx.reference,
            'status': 'done',
        }
        tx._handle_notification_data('momo', notification_data)

        return child_capture_tx

    def _send_void_request(self, amount_to_void=None):
        """ Override of `payment` to simulate a void request. """
        child_void_tx = super()._send_void_request(amount_to_void=amount_to_void)
        if self.provider_code != 'momo':
            return child_void_tx

        tx = child_void_tx or self
        notification_data = {'reference': tx.reference,
                             'status': 'cancel'}
        tx._handle_notification_data('momo', notification_data)

        return child_void_tx
