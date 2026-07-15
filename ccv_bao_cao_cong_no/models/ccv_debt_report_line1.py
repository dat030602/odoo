from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class BetaReportLine1(models.Model):
    _name = "ccv.debt.report.line1"
    _description = "Công nợ"
    _inherit = ["ccv.debt.report.mixin"]
    _order = 'account_id,partner_id,id,product_id'

