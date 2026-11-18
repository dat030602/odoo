# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    misa_inbot_id = fields.Many2one(
        'misa.inbot.document',
        string='MISA INBOT Document',
        readonly=True,
        copy=False,
        index=True,
        help='Linked MISA INBOT inbound or outbound document'
    )

    def action_post(self):
        """Override action_post to synchronize accounting date back to MISA INBOT."""
        res = super(AccountMove, self).action_post()
        for move in self:
            if move.misa_inbot_id:
                move.misa_inbot_id.action_sync_accounting_date(move)
        return res

    def _post(self, soft=True):
        """Ensure sync on posted state changes."""
        res = super(AccountMove, self)._post(soft=soft)
        for move in self:
            if move.misa_inbot_id:
                move.misa_inbot_id.action_sync_accounting_date(move)
        return res

    def _compute_payment_state(self):
        """Override to detect payment reconciliation changes and notify INBOT."""
        super(AccountMove, self)._compute_payment_state()
        for move in self:
            if move.misa_inbot_id and move.payment_state in ('paid', 'in_payment', 'partial', 'not_paid'):
                move.misa_inbot_id.action_sync_payment_status(move)
