import math
import time
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

DRIFT_THRESHOLD_PCT = 0.05
RECON_BATCH = 1000


class StockSnapshot(models.Model):
    _name = 'stock.snapshot'
    _description = 'Stock Balance Snapshot'
    _order = 'date desc'

    date = fields.Date(required=True, index=True)
    product_id = fields.Many2one('product.product', required=True, ondelete='cascade', index=True)
    location_id = fields.Many2one('stock.location', required=True, ondelete='cascade', index=True)
    quantity = fields.Float(digits='Product Unit of Measure', default=0.0)
    source = fields.Selection([
        ('cron', 'Scheduled'),
        ('manual', 'Manual'),
        ('reconcile', 'Reconciliation'),
    ], default='cron', required=True)
    created_at = fields.Datetime(default=fields.Datetime.now)

    _sql_constraints = [(
        'unique_snapshot',
        'UNIQUE (product_id, location_id, date)',
        'A snapshot already exists for this product/location/date.'
    )]

    @api.model
    def _get_nearest_snapshot(self, product_ids, location_ids, target_date):
        if not product_ids or not location_ids:
            return {}

        self.env.cr.execute("""
            SELECT DISTINCT ON (product_id, location_id)
                product_id, location_id, date, quantity
            FROM stock_snapshot
            WHERE product_id = ANY(%s)
              AND location_id = ANY(%s)
              AND date <= %s
            ORDER BY product_id, location_id, date DESC
        """, (list(product_ids), list(location_ids), target_date))

        return {(r[0], r[1]): (r[2], r[3]) for r in self.env.cr.fetchall()}

    @api.model
    def _sum_move_delta(self, product_ids, location_ids, from_date, to_date):
        from collections import defaultdict

        def run_query(loc_col):
            self.env.cr.execute(f"""
                SELECT sm.product_id,
                       sm.{loc_col}       AS location_id,
                       SUM(sm.quantity)   AS qty,
                       pt.uom_id          AS prod_uom_id,
                       sm.product_uom     AS move_uom_id
                FROM stock_move sm
                JOIN product_product pp ON pp.id = sm.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE sm.product_id  = ANY(%s)
                  AND sm.{loc_col}   = ANY(%s)
                  AND sm.state       = 'done'
                  AND sm.date        > %s
                  AND sm.date       <= %s
                GROUP BY sm.product_id, sm.{loc_col}, pt.uom_id, sm.product_uom
            """, (list(product_ids), list(location_ids), from_date, to_date))
            return self.env.cr.fetchall()

        def aggregate(rows):
            result = defaultdict(float)
            UoM = self.env['uom.uom']
            for product_id, location_id, qty, prod_uom_id, move_uom_id in rows:
                if move_uom_id != prod_uom_id:
                    qty = UoM.browse(move_uom_id)._compute_quantity(
                        qty, UoM.browse(prod_uom_id)
                    )
                result[(product_id, location_id)] += qty
            return result

        inbound = aggregate(run_query('location_dest_id'))
        outbound = aggregate(run_query('location_id'))
        return inbound, outbound

    @api.model
    def _compute_qty_at_date_fallback(self, product_ids, location_ids, target_date):
        if not product_ids or not location_ids:
            return {}

        self.env.cr.execute("""
            SELECT product_id, location_id, SUM(quantity)
            FROM stock_quant
            WHERE product_id = ANY(%s) AND location_id = ANY(%s)
            GROUP BY product_id, location_id
        """, (list(product_ids), list(location_ids)))
        current_map = {(r[0], r[1]): float(r[2]) for r in self.env.cr.fetchall()}

        def moves_after(loc_col):
            self.env.cr.execute(f"""
                SELECT sm.product_id,
                       sm.{loc_col}       AS location_id,
                       SUM(sm.quantity)   AS qty,
                       pt.uom_id          AS prod_uom_id,
                       sm.product_uom     AS move_uom_id
                FROM stock_move sm
                JOIN product_product pp ON pp.id = sm.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE sm.product_id  = ANY(%s)
                  AND sm.{loc_col}   = ANY(%s)
                  AND sm.state       = 'done'
                  AND sm.date        > %s
                GROUP BY sm.product_id, sm.{loc_col}, pt.uom_id, sm.product_uom
            """, (list(product_ids), list(location_ids), target_date))
            rows = self.env.cr.fetchall()
            result = {}
            UoM = self.env['uom.uom']
            for product_id, location_id, qty, prod_uom_id, move_uom_id in rows:
                if move_uom_id != prod_uom_id:
                    qty = UoM.browse(move_uom_id)._compute_quantity(
                        qty, UoM.browse(prod_uom_id)
                    )
                result[(product_id, location_id)] = result.get(
                    (product_id, location_id), 0.0
                ) + qty
            return result

        inbound_after = moves_after('location_dest_id')
        outbound_after = moves_after('location_id')

        result = {}
        for pid in product_ids:
            for lid in location_ids:
                current = current_map.get((pid, lid), 0.0)
                result[(pid, lid)] = (
                    current
                    - inbound_after.get((pid, lid), 0.0)
                    + outbound_after.get((pid, lid), 0.0)
                )
        return result

    @api.model
    def _upsert_snapshot(self, snap_date, product_id, location_id, quantity, source='cron'):
        self.env.cr.execute("""
            INSERT INTO stock_snapshot (date, product_id, location_id, quantity, source)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (product_id, location_id, date)
            DO UPDATE SET quantity   = EXCLUDED.quantity,
                          source     = EXCLUDED.source,
                          created_at = NOW()
        """, (snap_date, product_id, location_id, quantity, source))

    @api.model
    def _apply_snapshot_delta(self, product_id, location_id, delta, from_date):
        if not delta:
            return
        self.env.cr.execute("""
            UPDATE stock_snapshot
            SET quantity = quantity + %s
            WHERE product_id  = %s
              AND location_id = %s
              AND date        >= %s
        """, (delta, product_id, location_id, from_date))

    @api.model
    def _get_active_pairs(self, period_start, period_end):
        self.env.cr.execute("""
            SELECT DISTINCT product_id, location_id
            FROM stock_move
            WHERE state = 'done' AND date >= %s AND date <= %s

            UNION

            SELECT DISTINCT product_id, location_dest_id AS location_id
            FROM stock_move
            WHERE state = 'done' AND date >= %s AND date <= %s
        """, (period_start, period_end, period_start, period_end))
        return self.env.cr.fetchall()

    @api.model
    def _get_all_nonzero_pairs(self):
        self.env.cr.execute("""
            SELECT product_id, location_id
            FROM stock_quant
            WHERE quantity > 0
        """)
        return self.env.cr.fetchall()

    @api.model
    def run_monthly_snapshot(self, period_start=None, period_end=None):
        today = date.today()
        period_end = period_end or today
        period_start = period_start or period_end.replace(day=1)

        is_annual = (period_end.month == 12 and period_end.day == 31)
        pairs = (
            self._get_all_nonzero_pairs()
            if is_annual
            else self._get_active_pairs(period_start, period_end)
        )

        BATCH = 1000
        for i in range(0, len(pairs), BATCH):
            batch = pairs[i:i + BATCH]

            for (product_id, location_id) in batch:
                snap_map = self._get_nearest_snapshot(
                    [product_id], [location_id], period_end
                )
                snap = snap_map.get((product_id, location_id))
                base_qty = snap[1] if snap else 0.0
                base_date = snap[0] if snap else date.min

                inbound, outbound = self._sum_move_delta(
                    [product_id], [location_id], base_date, period_end
                )
                new_qty = (
                    base_qty
                    + inbound.get((product_id, location_id), 0.0)
                    - outbound.get((product_id, location_id), 0.0)
                )

                self._upsert_snapshot(period_end, product_id, location_id, new_qty, 'cron')

            self.env.cr.commit()
            time.sleep(0.1)

    @api.model
    def run_reconciliation(self, dry_run=True):
        cutoff_date = (datetime.now() - timedelta(minutes=5)).date()

        self.env.cr.execute("SELECT DISTINCT product_id, location_id FROM stock_snapshot")
        all_pairs = self.env.cr.fetchall()
        total = len(all_pairs)
        drifted = []

        for i in range(0, total, RECON_BATCH):
            batch = all_pairs[i:i + RECON_BATCH]
            product_ids = [p[0] for p in batch]
            location_ids = list({p[1] for p in batch})

            snap_map = self._get_nearest_snapshot(product_ids, location_ids, cutoff_date)

            self.env.cr.execute("""
                SELECT product_id, location_id, SUM(quantity)
                FROM stock_quant
                WHERE product_id = ANY(%s) AND location_id = ANY(%s)
                GROUP BY product_id, location_id
            """, (product_ids, location_ids))
            actual_map = {
                (r[0], r[1]): float(r[2]) for r in self.env.cr.fetchall()
            }

            for (product_id, location_id) in batch:
                snap = snap_map.get((product_id, location_id))
                base_qty = snap[1] if snap else 0.0
                base_date = snap[0] if snap else date.min

                inbound, outbound = self._sum_move_delta([product_id], [location_id], base_date, cutoff_date)
                expected = (
                    base_qty
                    + inbound.get((product_id, location_id), 0.0)
                    - outbound.get((product_id, location_id), 0.0)
                )
                actual = actual_map.get((product_id, location_id), 0.0)

                if not math.isclose(expected, actual, rel_tol=1e-6, abs_tol=1e-4):
                    key = (product_id, location_id, actual, expected)
                    drifted.append(key)

            time.sleep(0.05)

        if total and (len(drifted) / total) > DRIFT_THRESHOLD_PCT:
            self._alert_admin(f'{len(drifted)}/{total} snapshot pairs drifted — auto-fix ABORTED')
            self._log_recon(drifted, 'skipped_threshold', dry_run)
            return

        for (product_id, location_id, old_qty, new_qty) in drifted:
            self._log_recon_row(
                product_id, location_id, old_qty, new_qty,
                'snapshot_rebuild', dry_run
            )
            if not dry_run:
                corrupt_from = self._find_earliest_corrupt_snapshot(product_id, location_id)
                self._rebuild_snapshots_from(product_id, location_id, corrupt_from)

        if not dry_run:
            self.env.cr.commit()

    @api.model
    def _rebuild_snapshots_from(self, product_id, location_id, from_date):
        self.env.cr.execute("""
            DELETE FROM stock_snapshot
            WHERE product_id = %s AND location_id = %s AND date >= %s
        """, (product_id, location_id, from_date))

        snap_map = self._get_nearest_snapshot(
            [product_id], [location_id],
            from_date - relativedelta(days=1)
        )
        snap = snap_map.get((product_id, location_id))
        base_qty = snap[1] if snap else 0.0
        base_date = snap[0] if snap else date.min

        rebuild = from_date.replace(day=1)
        today = date.today()

        while rebuild <= today:
            period_end = (rebuild + relativedelta(months=1)) - relativedelta(days=1)

            inbound, outbound = self._sum_move_delta([product_id], [location_id], base_date, period_end)
            new_qty = (
                base_qty
                + inbound.get((product_id, location_id), 0.0)
                - outbound.get((product_id, location_id), 0.0)
            )

            self._upsert_snapshot(period_end, product_id, location_id, new_qty, 'reconcile')

            base_qty = new_qty
            base_date = period_end
            rebuild = rebuild + relativedelta(months=1)

        corrected_map = self._get_nearest_snapshot([product_id], [location_id], today)
        corrected = corrected_map.get((product_id, location_id))
        if corrected:
            self.env.cr.execute("""
                UPDATE stock_quant SET quantity = %s
                WHERE product_id = %s AND location_id = %s
            """, (corrected[1], product_id, location_id))

    @api.model
    def _find_earliest_corrupt_snapshot(self, product_id, location_id):
        self.env.cr.execute("""
            SELECT date, quantity FROM stock_snapshot
            WHERE product_id = %s AND location_id = %s
              AND date >= %s
            ORDER BY date DESC
        """, (product_id, location_id, date.today() - relativedelta(years=1)))

        snapshots = self.env.cr.fetchall()
        corrupt_from = date.today()

        for (snap_date, snap_qty) in snapshots:
            snap_map = self._get_nearest_snapshot([product_id], [location_id], snap_date - relativedelta(days=1))
            snap_prev = snap_map.get((product_id, location_id))
            base_qty = snap_prev[1] if snap_prev else 0.0
            base_date = snap_prev[0] if snap_prev else date.min

            inbound, outbound = self._sum_move_delta([product_id], [location_id], base_date, snap_date)
            recalc = (
                base_qty
                + inbound.get((product_id, location_id), 0.0)
                - outbound.get((product_id, location_id), 0.0)
            )

            if math.isclose(float(snap_qty), recalc, rel_tol=1e-6, abs_tol=1e-4):
                break
            corrupt_from = snap_date

        return corrupt_from

    @api.model
    def _alert_admin(self, message):
        _logger.warning('Stock Snapshot Alert: %s', message)

    @api.model
    def _log_recon(self, drifted, action, dry_run):
        for (product_id, location_id, old_qty, new_qty) in drifted:
            self._log_recon_row(product_id, location_id, old_qty, new_qty, action, dry_run)

    @api.model
    def _log_recon_row(self, product_id, location_id, old_qty, new_qty, action, dry_run):
        self.env['stock.snapshot.reconcile.log'].create({
            'product_id': product_id,
            'location_id': location_id,
            'old_quantity': old_qty,
            'new_quantity': new_qty,
            'drift': round(new_qty - old_qty, 4),
            'action': action,
            'dry_run': dry_run,
        })


class StockSnapshotReconcileLog(models.Model):
    _name = 'stock.snapshot.reconcile.log'
    _description = 'Stock Snapshot Reconciliation Log'
    _order = 'run_at desc'

    run_at = fields.Datetime(default=fields.Datetime.now)
    product_id = fields.Many2one('product.product', required=True)
    location_id = fields.Many2one('stock.location', required=True)
    old_quantity = fields.Float(digits='Product Unit of Measure')
    new_quantity = fields.Float(digits='Product Unit of Measure')
    drift = fields.Float(digits='Product Unit of Measure')
    action = fields.Char()
    dry_run = fields.Boolean(default=False)
    note = fields.Text()
