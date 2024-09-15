# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from werkzeug.urls import url_encode, url_join, url_parse
from odoo import _, api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class PaymentModelLine(models.Model):
    _name = "payment.model.line"

    name = fields.Char()
    key = fields.Char()
    value = fields.Char()
    payment_model_id = fields.Many2one(comodel_name="payment.model")
    payment_api_model_id = fields.Many2one(comodel_name="payment.api.model")
    type = fields.Selection(
        selection=[
            ("key", "Payment Key"),
            ("request", "Request"),
            ("response", "Response"),
        ]
    )

    @api.constrains("key")
    def _check_empty_key(self):
        if self.payment_key and not self.key:
            raise UserError(_("User must enter key."))
