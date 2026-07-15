from odoo import models, fields, api,_
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools import frozendict

import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super(AccountMove,self).action_post()
        for rec in self:
            if rec.state == 'posted':
                payments = rec._get_payment()
                if payments:
                    payments.reconcile_payments()
        return res

    def _get_payment(self):
        self.ensure_one()
        ids = []
        payments = self.env['account.payment'].sudo()
        if self.move_type == 'in_invoice':
            ids = self.line_ids.mapped('purchase_line_id').mapped('order_id').mapped('id')
            payments = payments.search(['|',('purchase_ids','in',ids),('purchase_id','in',ids)])
        elif self.move_type == 'out_invoice':
            ids = self.line_ids.mapped('sale_line_ids').mapped('order_id').mapped('id')
            payments = payments.search(['|',('sale_ids','in',ids),('sale_id','in',ids)])
        return payments
