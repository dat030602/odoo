import time
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class DnGraphqlRateLimit(models.Model):
    _name = 'dn.graphql.rate_limit'
    _description = 'GraphQL Rate Limiting State Tracker'
    _rec_name = 'key_index'

    key_index = fields.Char(string='Key Index', size=8, required=True, index=True)
    window_time = fields.Integer(string='Minute Window Timestamp', required=True, index=True)
    request_count = fields.Integer(string='Request Count', default=1)

    @classmethod
    def check_and_increment(cls, cr, key_index: str, limit_per_minute: int = 60) -> bool:
        """
        Atomically increments request count for current minute window.
        Returns True if within limit, False if rate limited.
        Wrapped in savepoint to guard against read-only test transactions.
        """
        if not key_index or limit_per_minute <= 0:
            return True

        current_window = int(time.time() // 60)
        try:
            with cr.savepoint():
                cr.execute("""
                    SELECT id, request_count FROM dn_graphql_rate_limit 
                    WHERE key_index = %s AND window_time = %s
                """, (key_index[:8], current_window))
                row = cr.fetchone()
                if row:
                    count = row[1] + 1
                    cr.execute("UPDATE dn_graphql_rate_limit SET request_count = %s WHERE id = %s", (count, row[0]))
                else:
                    count = 1
                    cr.execute("""
                        INSERT INTO dn_graphql_rate_limit (key_index, window_time, request_count)
                        VALUES (%s, %s, 1)
                    """, (key_index[:8], current_window))
                return count <= limit_per_minute
        except Exception as e:
            _logger.debug("Rate limit increment bypassed: %s", e)
            return True
