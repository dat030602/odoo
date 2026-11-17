from odoo import fields, models


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    name = fields.Datetime(
        string='Date & Time',
        required=True,
        index=True,
        default=fields.Datetime.now,
    )

    _unique_name_per_day = models.Constraint(
        'unique (name, currency_id, company_id)',
        'Only one currency rate per second is allowed for each currency and company!',
    )
