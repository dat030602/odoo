from odoo import api, models


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    @api.depends('name', 'rate', 'currency_id', 'company_rate')
    def _compute_display_name(self):
        for rate in self:
            date_str = str(rate.name) if rate.name else ''
            curr_name = rate.currency_id.name or ''
            val = rate.company_rate or rate.rate or 0.0
            rate.display_name = f"{date_str} [{curr_name}: {val:g}]"
