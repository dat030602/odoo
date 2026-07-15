from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class fleet_vehicle(models.Model):
    _inherit = "fleet.vehicle"

    end_date = fields.Date(string="Ngày hết hạn")
