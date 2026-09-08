from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        if self.env.context.get('skip_snapshot_sync'):
            return super().write(vals)

        SENSITIVE = {
            'quantity', 'location_id', 'location_dest_id',
            'date', 'state', 'product_id'
        }
        if not (SENSITIVE & set(vals.keys())):
            return super().write(vals)

        pre_data = {
            m.id: {
                'product_id': m.product_id.id,
                'location_id': m.location_id.id,
                'location_dest_id': m.location_dest_id.id,
                'quantity': m.quantity,
                'date': m.date.date() if hasattr(m.date, 'date') else m.date,
            }
            for m in self.filtered(lambda m: m.state == 'done')
        }

        res = super().write(vals)

        Snapshot = self.env['stock.snapshot']

        for move_id, old in pre_data.items():
            Snapshot._apply_snapshot_delta(old['product_id'], old['location_id'], +old['quantity'], old['date'])
            Snapshot._apply_snapshot_delta(old['product_id'], old['location_dest_id'], -old['quantity'], old['date'])

        for move in self.filtered(lambda m: m.state == 'done'):
            move_date = move.date.date() if hasattr(move.date, 'date') else move.date
            Snapshot._apply_snapshot_delta(move.product_id.id, move.location_id.id, -move.quantity, move_date)
            Snapshot._apply_snapshot_delta(move.product_id.id, move.location_dest_id.id, +move.quantity, move_date)

        return res

    def unlink(self):
        Snapshot = self.env['stock.snapshot']
        for move in self.filtered(lambda m: m.state == 'done'):
            move_date = move.date.date() if hasattr(move.date, 'date') else move.date
            Snapshot._apply_snapshot_delta(move.product_id.id, move.location_id.id, +move.quantity, move_date)
            Snapshot._apply_snapshot_delta(move.product_id.id, move.location_dest_id.id, -move.quantity, move_date)
        return super().unlink()

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)

        Snapshot = self.env['stock.snapshot']
        for move in self.with_context(skip_snapshot_sync=True):
            move_date = move.date.date() if hasattr(move.date, 'date') else move.date
            Snapshot._apply_snapshot_delta(move.product_id.id, move.location_id.id, -move.quantity, move_date)
            Snapshot._apply_snapshot_delta(move.product_id.id, move.location_dest_id.id, +move.quantity, move_date)

        return res
