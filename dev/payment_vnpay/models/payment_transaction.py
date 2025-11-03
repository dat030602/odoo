import logging

from odoo import _, models, api
from odoo.exceptions import ValidationError
from odoo.tools import get_lang

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    
    # Business method
    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return VNPay-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'vnpay':
            return res
        payload = self.provider_id._prepare_payload_vnpay(self.amount, self.reference)
        _logger.info("VNPay: payload: %s", payload)
        return { 'payload': payload, 'url': self.provider_id._generate_url_vnpay(payload) }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on VNPay data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'vnpay' or len(tx) == 1:
            return tx
        reference = notification_data.get('reference')
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'vnpay')])
        if not tx:
            raise ValidationError("VNPay: " + _("No transaction found matching reference %s.", reference))
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on VNPay data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'vnpay':
            return
        self.provider_reference = f'vnpay-{self.reference}'
        payment_status = notification_data.get('status')
        if payment_status == 'pending':
            self._set_pending()
        elif payment_status == 'authorized':
            self._set_authorized()
        elif payment_status == 'paid':
            self._set_done()
        elif payment_status in ['expired', 'canceled', 'failed']:
            self._set_canceled("VNPay: " + _("Canceled payment with status: %s", payment_status))
        else:
            _logger.info("received data with invalid payment status (%s) for transaction with reference %s", payment_status, self.reference)
            self._set_error("VNPay: " + _("Received data with invalid payment status: %s", payment_status))
