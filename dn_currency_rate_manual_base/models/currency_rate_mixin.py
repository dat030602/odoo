from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CurrencyRateMixin(models.AbstractModel):
    _name = 'currency.rate.mixin'
    _description = 'Currency Rate Mixin'

    rate_mode = fields.Selection(
        selection=[
            ('default', 'Default'),
            ('custom', 'Custom'),
        ],
        string='Rate Mode',
        default='default',
        required=True,
        copy=True,
        help="Rate mode for document currency conversion:\n"
             "- Default: standard Odoo rate lookup on document date.\n"
             "- Custom: select a specific historical exchange rate.",
    )
    selected_rate_id = fields.Many2one(
        comodel_name='res.currency.rate',
        string='Selected Rate',
        copy=True,
        domain="[('currency_id', '=', currency_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Select a specific historical rate.",
    )

    @api.constrains('rate_mode', 'selected_rate_id')
    def _check_rate_mode_values(self):
        for record in self:
            if record.rate_mode == 'custom' and not record.selected_rate_id:
                raise ValidationError(self.env._("Please select a historical currency rate when 'Custom' mode is chosen."))

    @api.onchange('rate_mode')
    def _onchange_rate_mode(self):
        for record in self:
            if record.rate_mode == 'default':
                record.selected_rate_id = False

    def _get_rate_context(self):
        """
        Hook returning a tuple (company_currency, document_currency, company, date)
        Override in inheriting models.
        """
        self.ensure_one()
        return (self.env.company.currency_id, getattr(self, 'currency_id', False), getattr(self, 'company_id', self.env.company), fields.Date.context_today(self))

    def _get_dynamic_rate(self, auto_rate=None):
        """
        Compute effective rate based on rate_mode:
        Returns rate in units of document currency per company currency
        (standard rate format in account.move, sale.order, purchase.order).
        """
        self.ensure_one()
        company_currency, doc_currency, company, rate_date = self._get_rate_context()

        if not doc_currency or not company_currency or doc_currency == company_currency:
            return 1.0

        if self.rate_mode == 'custom':
            if self.selected_rate_id:
                comp_rate = company_currency._get_rates(company, rate_date).get(company_currency.id, 1.0)
                selected_curr_rate = self.selected_rate_id.rate
                return (selected_curr_rate or 1.0) / comp_rate
            return auto_rate or 1.0

        # 'default'
        return auto_rate or 1.0
