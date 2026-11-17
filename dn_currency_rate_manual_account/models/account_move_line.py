from contextlib import contextmanager
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @contextmanager
    def _sync_invoice(self, container):
        # Prevent premature re-division of payment_term lines (which causes rounding imbalance on invoice date/rate change)
        pt_lines = container['records'].filtered(lambda l: l.display_type == 'payment_term')
        with self.env.protecting([self._fields['balance']], pt_lines):
            with super()._sync_invoice(container):
                yield
