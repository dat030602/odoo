# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import uuid
import requests

from werkzeug.urls import url_encode, url_join, url_parse
from odoo import _, api, fields, models


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _name = "payment.api.model"

    name = fields.Char()
    methob = fields.Selection(
        selection=[
            ("get", "GET"),
            ("post", "POST"),
            ("put", "PUT"),
            ("delete", "DELETE"),
        ]
    )

    type = fields.Selection(
        selection=[
            ("request", "Request"),
            ("response", "Response"),
        ]
    )

    payment_model_id = fields.Many2one(comodel_name="payment.model")
    payment_model_ids = fields.One2many(comodel_name="payment.model.line", inverse_name="payment_api_model_id")
    payment_response_ids = fields.One2many(comodel_name="payment.response", inverse_name="payment_api_model_id")
