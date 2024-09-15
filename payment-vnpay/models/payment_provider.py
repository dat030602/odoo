# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.payment_vnpay import utils

_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'
    code = fields.Selection(
        selection_add=[('vnpay', "VNPay")], ondelete={'vnpay': 'set default'})
    vnpay_tmn_code = fields.Char(
        string="TMN Code", help="The key solely used to identify the account with VNPay",
        required_if_provider='vnpay')
    vnpay_hash_secret_key = fields.Char(
        string="Hash Secret Key", required_if_provider='vnpay', groups='base.group_system')

    # === COMPUTE METHODS ===#

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'vnpay').show_credentials_page = True

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'vnpay').update({
            'support_express_checkout': False,
            'support_manual_capture': False,
            'support_tokenization': False,
            'support_refund': 'full_only',
        })

    # === CONSTRAINT METHODS ===#

    @api.constrains('state', 'vnpay_tmn_code', 'vnpay_hash_secret_key')
    def _check_state_of_connected_account_is_never_test(self):
        """ Check that the provider of a connected account can never been set to 'test'.

        This constraint is defined in the present module to allow the export of the translation
        string of the `ValidationError` should it be raised by modules that would fully implement
        VNPay Connect.

        Additionally, the field `state` is used as a trigger for this constraint to allow those
        modules to indirectly trigger it when writing on custom fields. Indeed, by always writing on
        `state` together with writing on those custom fields, the constraint would be triggered.

        :return: None
        :raise ValidationError: If the provider of a connected account is set in state 'test'.
        """
        if self.filtered(lambda p: p.code == 'vnpay' and p.state in ('test', 'enable')):
            if self.vnpay_tmn_code == '' or self.vnpay_hash_secret_key == '':
                raise UserError(_("User must enter the TMN code and Hash Secret Key."))

    # === ACTION METHODS === #

    # === BUSINESS METHODS - PAYMENT FLOW === #

    # === BUSINESS METHODS - GETTERS ===#

    def _vnpay_get_tmn_code(self):
        """ Return the publishable key of the provider.

        This getter allows fetching the publishable key from a QWeb template and through VNPay's
        utils.

        Note: `self.ensure_one()

        :return: The publishable key.
        :rtype: str
        """
        self.ensure_one()

        return utils.get_tmn_code(self.sudo())

    def _vnpay_get_hash_secret_key(self):
        """ Return the publishable key of the provider.

        This getter allows fetching the publishable key from a QWeb template and through VNPay's
        utils.

        Note: `self.ensure_one()

        :return: The publishable key.
        :rtype: str
        """
        self.ensure_one()

        return utils.get_hash_secret_key(self.sudo())
