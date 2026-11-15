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

    _unique_window_key = models.Constraint(
        'UNIQUE(key_index, window_time)',
        'Key index and minute window must be unique.'
    )

    @classmethod
    def check_and_increment(cls, cr, key_index: str, limit_per_minute: int = 60) -> bool:
        if not key_index or limit_per_minute <= 0:
            return True

        current_window = int(time.time() // 60)
        try:
            with cr.savepoint():
                cr.execute("""
                    INSERT INTO dn_graphql_rate_limit (key_index, window_time, request_count)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (key_index, window_time)
                    DO UPDATE SET request_count = dn_graphql_rate_limit.request_count + 1
                    RETURNING request_count;
                """, (key_index[:8], current_window))
                row = cr.fetchone()
                count = row[0] if row else 1
                return count <= limit_per_minute
        except Exception as e:
            _logger.error("Rate limit check failed due to database exception: %s", e)
            return False  # Fail-closed
