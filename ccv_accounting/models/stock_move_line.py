from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    account_id = fields.Many2one("account.account", string="Tài khoản", related='move_id.account_id')
