from contextlib import contextmanager

from odoo import api, fields, models


class _LockedPartnerContainer(dict):
    """Wrapper dictionary that excludes moves with vn_allow_different_partner from records during sync."""

    def __init__(self, original_container):
        super().__init__()
        self._container = original_container

    def __getitem__(self, key):
        recordset = self._container[key]
        if key == 'records':
            return recordset.filtered(lambda move: not move.vn_allow_different_partner)
        return recordset

    def __setitem__(self, key, value):
        self._container[key] = value

    def __contains__(self, key):
        return key in self._container

    def __iter__(self):
        return iter(self._container)

    def __len__(self):
        return len(self._container)

    def get(self, key, default_value=None):
        if key in self._container:
            return self[key]
        return default_value


class AccountMove(models.Model):
    _inherit = 'account.move'

    vn_allow_different_partner = fields.Boolean(
        string="Allow Different Line Partner",
        default=False,
        tracking=True,
        help="When unchecked, follows standard Odoo behavior (lines sync with invoice partner). When checked, allows lines to have a different partner when created, but lines cannot be updated with a different partner afterwards.",
    )

    @api.onchange('partner_id')
    def _inverse_partner_id(self):
        unlocked_invoices = self.filtered(lambda move: not move.vn_allow_different_partner)
        if unlocked_invoices:
            super(AccountMove, unlocked_invoices)._inverse_partner_id()

    @contextmanager
    def _sync_invoice(self, container):
        if isinstance(container, dict) and 'records' in container:
            wrapped_container = _LockedPartnerContainer(container)
            with super()._sync_invoice(wrapped_container):
                yield
        else:
            with super()._sync_invoice(container):
                yield

    def _post(self, soft=True):
        moves_with_diff = self.filtered('vn_allow_different_partner')
        line_partner_snapshot = {
            line: line.partner_id
            for move in moves_with_diff
            for line in move.line_ids
        }
        posted_moves = super(AccountMove, self.with_context(bypass_line_partner_lock=True))._post(soft=soft)
        for line, original_partner in line_partner_snapshot.items():
            if line.exists() and line.partner_id != original_partner:
                line.with_context(bypass_line_partner_lock=True).partner_id = original_partner
        return posted_moves
