from platform import machine
from odoo import models, fields, api
import logging
import requests
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import json

_logger = logging.getLogger(__name__)

class CcvSalePlanExportLine2(models.Model):
    _inherit = "ccv.sale.plan.export.line2"

    tag_ids = fields.Many2many('mrp.bom.tags', string="Thẻ", compute="_compute_tags", store=True)

    @api.depends('bom_id')
    def _compute_tags(self):
        for record in self:
            if record.bom_id:
                record.tag_ids = record.bom_id.tag_ids
            else:
                record.tag_ids = False
