# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import uuid
import requests

from werkzeug.urls import url_encode, url_join, url_parse
from odoo import _, api, fields, models


_logger = logging.getLogger(__name__)


class PaymentResponse(models.Model):
    _name = "payment.response"

    name = fields.Char(string="Name", required=True)
    json_data  = fields.Char()
    status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("failed", "Failed"),
            ("processing", "Processing"),
            ("done", "Done"),
        ], default="pending"
    )
    payment_api_model_id = fields.Many2one(comodel_name="payment.api.model")
    