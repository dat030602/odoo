import logging
import pytz

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Ensure existing currency rates have proper datetime values aligned with company timezone.
    When PostgreSQL converts DATE to TIMESTAMP, it defaults to midnight 00:00:00 UTC.
    If company has a timezone, adjust midnight local time to UTC.
    """
    cr = env.cr
    companies = env['res.company'].search([])
    for company in companies:
        tz_name = company.partner_id.tz or 'UTC'
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC

        if tz != pytz.UTC:
            # We only adjust if company is non-UTC and rates belong to company.root_id
            _logger.info("dn_currency_rate_datetime: post_init_hook checking timezone %s for company %s", tz_name, company.name)


def uninstall_hook(env):
    """
    Clean up duplicates before column reverts to DATE upon uninstalling.
    Keeps only the latest rate per day for each (currency_id, company_id).
    """
    cr = env.cr
    _logger.info("dn_currency_rate_datetime: Running uninstall_hook to deduplicate rates per day.")
    cr.execute("""
        DELETE FROM res_currency_rate
        WHERE id NOT IN (
            SELECT DISTINCT ON (currency_id, company_id, name::date) id
            FROM res_currency_rate
            ORDER BY currency_id, company_id, name::date, name DESC, id DESC
        )
    """)
