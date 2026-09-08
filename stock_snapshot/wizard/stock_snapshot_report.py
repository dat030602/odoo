from odoo import models, fields, api


class StockSnapshotReport(models.TransientModel):
    _name = 'stock.snapshot.report'
    _description = 'Stock Balance Snapshot Viewer'

    date = fields.Date(
        string='As of Date',
        required=True,
        default=fields.Date.today,
        help='Show stock balance as it was at the end of this date.',
    )
    location_ids = fields.Many2many(
        'stock.location',
        string='Locations',
        domain=[('usage', '=', 'internal')],
        help='Leave empty to include all internal locations.',
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        context={'active_test': False},
        help='Leave empty to include all products.',
    )
    show_zero_qty = fields.Boolean(
        string='Show Zero Quantity',
        default=False,
        help='Include lines where computed quantity = 0.',
    )
    show_archived = fields.Boolean(
        string='Show Archived Products',
        default=False,
        help='Include products that have been archived (active = False).',
    )

    def action_compute(self):
        self.ensure_one()
        target_date = self.date
        Snapshot = self.env['stock.snapshot']

        location_ids = self.location_ids.ids
        product_ids = self.product_ids.ids

        action = self.env.ref('action_stock_snapshot').sudo().read()[0]
        action['domain'] = [('date', '=', target_date)]
        action['context'] = {'search_default_group_by_product': 1}
        action['views'] = [(False, 'list'), (False, 'kanban')]

        if not product_ids:
            product_domain = []
            if self.show_archived:
                product_domain += ['|', ('active', '=', True), ('active', '=', False)]
            else:
                product_domain += [('active', '=', True)]
            products = self.env['product.product'].with_context(active_test=False)\
                .search(product_domain)
            product_ids = products.ids

        if location_ids:
            location_ids = self.env['stock.location'].search([
                ('id', 'child_of', location_ids),
                ('usage', '=', 'internal'),
            ]).ids
        else:
            location_ids = self.env['stock.location'].search([
                ('usage', '=', 'internal'),
            ]).ids

        if not product_ids or not location_ids:
            return action

        self.env.cr.execute("""
            SELECT DISTINCT product_id, location_id
            FROM stock_move
            WHERE product_id = ANY(%s)
              AND location_id = ANY(%s)
              AND state = 'done'
              AND date <= %s

            UNION

            SELECT DISTINCT product_id, location_dest_id AS location_id
            FROM stock_move
            WHERE product_id = ANY(%s)
              AND location_dest_id = ANY(%s)
              AND state = 'done'
              AND date <= %s
        """, (
            product_ids, location_ids, target_date,
            product_ids, location_ids, target_date,
        ))
        pairs = self.env.cr.fetchall()

        BATCH = 1000
        for i in range(0, len(pairs), BATCH):
            batch = pairs[i:i + BATCH]
            p_ids = list({p[0] for p in batch})
            l_ids = list({p[1] for p in batch})

            snap_map = Snapshot._get_nearest_snapshot(p_ids, l_ids, target_date)

            no_snap = [(pid, lid) for (pid, lid) in batch if not snap_map.get((pid, lid))]
            fallback_map = {}
            if no_snap:
                no_snap_p_ids = list({p for p, l in no_snap})
                no_snap_l_ids = list({l for p, l in no_snap})
                fallback_map = Snapshot._compute_qty_at_date_fallback(no_snap_p_ids, no_snap_l_ids, target_date)

            for (product_id, location_id) in batch:
                snap = snap_map.get((product_id, location_id))
                if snap:
                    base_qty = snap[1]
                    base_date = snap[0]
                    inbound, outbound = Snapshot._sum_move_delta([product_id], [location_id], base_date, target_date)
                    new_qty = (
                        base_qty
                        + inbound.get((product_id, location_id), 0.0)
                        - outbound.get((product_id, location_id), 0.0)
                    )
                else:
                    new_qty = fallback_map.get((product_id, location_id), 0.0)

                if not self.show_zero_qty and not new_qty:
                    continue

                Snapshot._upsert_snapshot(target_date, product_id, location_id, new_qty, 'manual')

            self.env.cr.commit()

        return action
