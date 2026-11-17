from datetime import date, datetime, time
import pytz

from odoo import fields, models
from odoo.tools import SQL


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _normalize_rate_datetime(self, company, rate_date):
        """
        Normalize date or datetime into a UTC datetime string or datetime object.
        If a date (or string 'YYYY-MM-DD') is provided, it considers the end of that day in company timezone
        so that any rates published during that day are taken into account.
        """
        if not rate_date:
            return fields.Datetime.now()

        if isinstance(rate_date, str):
            if len(rate_date) == 10:
                rate_date = fields.Date.from_string(rate_date)
            else:
                return fields.Datetime.from_string(rate_date)

        if isinstance(rate_date, datetime):
            return rate_date

        if isinstance(rate_date, date):
            # Convert date to end of day in company's timezone, then to UTC
            tz_name = (company and company.partner_id.tz) or self.env.user.tz or 'UTC'
            try:
                local_tz = pytz.timezone(tz_name)
            except Exception:
                local_tz = pytz.UTC

            local_dt = local_tz.localize(datetime.combine(rate_date, time.max))
            utc_dt = local_dt.astimezone(pytz.UTC).replace(tzinfo=None)
            return utc_dt

        return rate_date

    def _get_rates(self, company, date):
        if not self.ids:
            return {}

        rate_datetime = self._normalize_rate_datetime(company, date)

        currency_query = self._as_query(ordered=False)
        currency_id = self.env['res.currency']._field_to_sql(currency_query.table, 'id')
        Rate = self.env['res.currency.rate']
        rate_query = Rate._search([
            ('name', '<=', rate_datetime),
            ('company_id', 'in', (False, company.root_id.id)),
        ], order='company_id.id, name DESC', limit=1)
        rate_query.add_where(SQL("%s = %s", Rate._field_to_sql(rate_query.table, 'currency_id'), currency_id))
        rate_fallback = Rate._search([
            ('company_id', 'in', (False, company.root_id.id)),
        ], order='company_id.id, name ASC', limit=1)
        rate_fallback.add_where(SQL("%s = %s", Rate._field_to_sql(rate_fallback.table, 'currency_id'), currency_id))
        rate = Rate._field_to_sql(rate_query.table, 'rate')
        return dict(self.env.execute_query(currency_query.select(
            currency_id,
            SQL("COALESCE((%s), (%s), 1.0)", rate_query.select(rate), rate_fallback.select(rate))
        )))
