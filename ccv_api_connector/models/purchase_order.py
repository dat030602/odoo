from odoo import models, fields, api
import logging
import json
from datetime import datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    abbreviation = fields.Char(
        string="Tên viết tắt",
        related='partner_id.abbreviation',
        store=True,
        readonly=True,
    )

    def name_get(self):
        result = []
        for order in self:
            name = order.name or ''
            partner_name = order.partner_id.name or ''
            display_name = f"{name} - {partner_name}" if partner_name else name
            result.append((order.id, display_name))
        return result