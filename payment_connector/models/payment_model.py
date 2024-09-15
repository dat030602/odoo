# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import uuid
import requests

from werkzeug.urls import url_encode, url_join, url_parse
from odoo import _, api, fields, models


_logger = logging.getLogger(__name__)


class PaymentModel(models.Model):
    _name = "payment.model"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(
        string="Code", help="The technical code of this payment method.", required=True
    )
    sequence = fields.Integer(string="Sequence", default=1)
    provider_ids = fields.Many2many(
        string="Providers",
        help="The list of providers supporting this payment method.",
        comodel_name="payment.provider",
    )
    image = fields.Image(
        string="Image",
        help="The base image used for this payment method; in a 64x64 px format.",
        max_width=64,
        max_height=64,
        required=True,
    )
    support_tokenization = fields.Boolean(
        string="Tokenization Supported",
        help="Tokenization is the process of saving the payment details as a token that can later"
        " be reused without having to enter the payment details again.",
    )
    support_express_checkout = fields.Boolean(
        string="Express Checkout Supported",
        help="Express checkout allows customers to pay faster by using a payment method that"
        " provides all required billing and shipping information, thus allowing to skip the"
        " checkout process.",
    )
    support_refund = fields.Selection(
        string="Type of Refund Supported",
        selection=[("full_only", "Full Only"), ("partial", "Partial")],
        help="Refund is a feature allowing to refund customers directly from the payment in Odoo.",
    )
    supported_country_ids = fields.Many2many(
        string="Supported Countries",
        comodel_name="res.country",
        help="The list of countries in which this payment method can be used (if the provider"
        " allows it). In other countries, this payment method is not available to customers.",
    )
    supported_currency_ids = fields.Many2many(
        string="Supported Currencies",
        comodel_name="res.currency",
        help="The list of currencies for that are supported by this payment method (if the provider"
        " allows it). When paying with another currency, this payment method is not available "
        "to customers.",
    )

    model_api_ids = fields.One2many(
        string="APIs", comodel_name="payment.api.model", inverse_name="payment_model_id"
    )
    key_ids = fields.One2many(
        string="Keys", comodel_name="payment.model.line", inverse_name="payment_model_id"
    )
