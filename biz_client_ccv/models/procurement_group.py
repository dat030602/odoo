# -*- coding: utf-8 -*-

import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    @api.model
    def run_scheduler(self, use_new_cursor=False, company_id=False):
        return super(ProcurementGroup, self.with_context(custom_cron_run_scheduler=True)).run_scheduler(use_new_cursor=use_new_cursor, company_id=company_id)