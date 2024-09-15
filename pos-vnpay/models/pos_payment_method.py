# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import werkzeug

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)

TIMEOUT = 10

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('vnpay', 'VNPay')]

    # VNPay
    name
    image_128 = fields.Image("Image VNPay", max_width=128, max_height=128)

    def _get_vnpay_payment_provider(self):
        vnpay_payment_provider = self.env['payment.provider'].search([
            ('code', '=', 'vnpay'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not vnpay_payment_provider:
            raise UserError(
                _("VNPay payment provider for company %s is missing", self.env.company.name))

        return vnpay_payment_provider

    @api.model
    def _get_vnpay_secret_key(self):
        vnpay_secret_key = self._get_vnpay_payment_provider().vnpay_secret_key

        if not vnpay_secret_key:
            raise ValidationError(
                _('Complete the VNPay onboarding for company %s.', self.env.company.name))

        return vnpay_secret_key

    def action_vnpay_key(self):
        res_id = self._get_vnpay_payment_provider().id
        # Redirect
        return {
            'name': _('VNPay'),
            'res_model': 'payment.provider',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': res_id,
        }
