# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import uuid
import requests

from werkzeug.urls import url_encode, url_join, url_parse
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.payment_momo import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('momo', "Momo")], ondelete={'momo': 'set default'})
    momo_partner_code = fields.Char(
        string="Partner Code", help="Định danh duy nhất của tài khoản M4B của bạn",
        required_if_provider='momo')
    momo_access_key = fields.Char(
        string="Access Key", help="Mã cấp quyền truy cập vào hệ thống MoMo",
        required_if_provider='momo')
    momo_public_key = fields.Char(
        string="Public Key", help="Sử dụng để tạo mã hoá dữ liệu bằng thuật toán RSA",
        required_if_provider='momo')
    momo_secret_key = fields.Char(
        string="Secret Key", help="Dùng để tạo chữ ký điện tử digital signature",
        required_if_provider='momo', groups='base.group_system')

    # === COMPUTE METHODS ===#

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'momo').show_credentials_page = True

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'momo').update({
            'support_express_checkout': False,
            'support_manual_capture': False,
            'support_tokenization': False,
            'support_refund': 'full_only',
        })

    # === CONSTRAINT METHODS ===#

    @api.constrains('state', 'momo_partner_code', 'momo_access_key', 'momo_public_key', 'momo_secret_key')
    def _check_state_of_connected_account_is_never_test(self):
        """ Check that the provider of a connected account can never been set to 'test'.

        This constraint is defined in the present module to allow the export of the translation
        string of the `ValidationError` should it be raised by modules that would fully implement
        Momo Connect.

        Additionally, the field `state` is used as a trigger for this constraint to allow those
        modules to indirectly trigger it when writing on custom fields. Indeed, by always writing on
        `state` together with writing on those custom fields, the constraint would be triggered.

        :return: None
        :raise ValidationError: If the provider of a connected account is set in state 'test'.
        """
        if self.filtered(lambda p: p.code == 'momo' and p.state in ('test', 'enable')):
            if self.momo_partner_code == '' and self.momo_access_key == '' and \
               self.momo_public_key == '' and self.momo_secret_key == '':
                raise UserError(_("User must enter the Partner Code, Access Key, Public Key and Secret Key."))

    # === ACTION METHODS === #

    # === BUSINESS METHODS - PAYMENT FLOW === #

    # === BUSINESS METHODS - GETTERS ===#

    def _momo_get_partner_code(self):
        """ Return the Partner Code of the provider.

        This getter allows fetching the Partner Code from a QWeb template and through Momo's
        utils.

        Note: `self.ensure_one()

        :return: The Partner Code.
        :rtype: str
        """
        self.ensure_one()

        return payment_utils.get_momo_partner_code(self.sudo())
    def _momo_get_access_key(self):
        """ Return the Access Key of the provider.

        This getter allows fetching the Access Key from a QWeb template and through Momo's
        utils.

        Note: `self.ensure_one()

        :return: The Access Key.
        :rtype: str
        """
        self.ensure_one()

        return payment_utils.get_momo_access_key(self.sudo())
    def _momo_get_public_key(self):
        """ Return the Public Key of the provider.

        This getter allows fetching the Public Key from a QWeb template and through Momo's
        utils.

        Note: `self.ensure_one()

        :return: The Public Key.
        :rtype: str
        """
        self.ensure_one()

        return payment_utils.get_momo_public_key(self.sudo())
    def _momo_get_secret_key(self):
        """ Return the Secret Key of the provider.

        This getter allows fetching the Secret Key from a QWeb template and through Momo's
        utils.

        Note: `self.ensure_one()

        :return: The Secret Key.
        :rtype: str
        """
        self.ensure_one()

        return payment_utils.get_momo_secret_key(self.sudo())
