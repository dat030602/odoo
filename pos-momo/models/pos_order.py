# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
import logging
_logger = logging.getLogger(__name__)
class PosOrder(models.Model):
    _inherit = 'pos.order'
    def add_payment(self, data):
        """Create a new payment for the order"""
        self.ensure_one()
        newData = data
        account_payment = self.env['account.payment'].search([('pos_order_id', '=', self['id'])], limit=1)
        if len(account_payment) > 0:
            if 'Momo' in account_payment['payment_method_line_id'].display_name or 'Momo' in account_payment['payment_method_line_id'].name:
                account_payment.action_post()
                if isinstance(newData, dict):
                    newData['online_account_payment_id'] = account_payment['id']
                else:
                    setattr(newData, 'online_account_payment_id', account_payment['id'])
        self.env['pos.payment'].create(newData)
        self.amount_paid = sum(self.payment_ids.mapped('amount'))
