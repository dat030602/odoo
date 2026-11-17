from contextlib import contextmanager
from odoo import api, fields, models


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'currency.rate.mixin']

    def _get_rate_context(self):
        self.ensure_one()
        rate_date = self.invoice_date or self.date or fields.Date.context_today(self)
        return (self.company_currency_id, self.currency_id, self.company_id, rate_date)

    @api.depends(
        'currency_id',
        'company_currency_id',
        'company_id',
        'invoice_date',
        'taxable_supply_date',
        'rate_mode',
        'selected_rate_id',
    )
    def _compute_invoice_currency_rate(self):
        super()._compute_invoice_currency_rate()
        for move in self:
            if move.is_invoice(include_receipts=True) and move.currency_id != move.company_currency_id:
                if move.rate_mode == 'custom':
                    move.invoice_currency_rate = move._get_dynamic_rate(auto_rate=move.expected_currency_rate)

    def refresh_invoice_currency_rate(self):
        super().refresh_invoice_currency_rate()
        for move in self:
            move.rate_mode = 'default'
            move.selected_rate_id = False

    @contextmanager
    def _sync_dynamic_lines(self, container):
        with super()._sync_dynamic_lines(container):
            yield
            for move in container['records'].filtered(lambda m: m.is_invoice(True)):
                pt_lines = move.line_ids.filtered(lambda l: l.display_type == 'payment_term')
                if len(pt_lines) == 1:
                    other_lines = move.line_ids - pt_lines
                    expected_balance = -sum(other_lines.mapped('balance'))
                    if pt_lines.balance != expected_balance:
                        pt_lines.balance = expected_balance

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if not default_values_list:
            default_values_list = [{} for _ in self]

        for move, default_values in zip(self, default_values_list):
            if move.rate_mode and move.rate_mode != 'default':
                default_values.update({
                    'rate_mode': move.rate_mode,
                    'selected_rate_id': move.selected_rate_id.id,
                })

        return super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
