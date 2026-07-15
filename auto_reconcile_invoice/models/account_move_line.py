from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # def _action_auto_reconcile(self):
    #     self.ensure_one()
    #     lines = self.env['account.move.line'].browse(record.id)
    #     lines += self.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
    #     return lines.reconcile()

