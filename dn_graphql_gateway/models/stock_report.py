from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DnGraphqlStockReport(models.AbstractModel):
    _name = 'dn.graphql.stock.report'
    _description = 'GraphQL Inventory In-Out-Balance Report Service'

    @api.model
    def action_bao_cao_xuat_nhap_ton(self, product_id, location_id, date_from=None, date_to=None, states=None):
        """
        Báo cáo Xuất - Nhập - Tồn (Thẻ kho chi tiết) cho 1 sản phẩm tại 1 địa điểm kho.
        Tính toán:
        1. Số dư đầu kỳ (Opening Balance)
        2. Các phát sinh trong kỳ (Movements) kèm Tồn lũy kế (Running Balance)
        3. Tồn cuối kỳ (Closing Balance)
        """
        product = self.env['product.product'].browse(int(product_id))
        if not product.exists():
            raise UserError(_("Product ID %s does not exist.") % product_id)

        location = self.env['stock.location'].browse(int(location_id))
        if not location.exists():
            raise UserError(_("Location ID %s does not exist.") % location_id)

        states = states or ['done']
        d_from = str(date_from) if date_from else '1970-01-01 00:00:00'
        d_to = str(date_to) if date_to else datetime.utcnow().strftime('%Y-%m-%d 23:59:59')

        cr = self.env.cr

        # 1. Tính Số dư đầu kỳ (Opening Balance)
        query_opening = """
            SELECT
                COALESCE(SUM(CASE WHEN location_dest_id = %s THEN quantity ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN location_id = %s THEN quantity ELSE 0 END), 0) AS opening_qty
            FROM stock_move
            WHERE product_id = %s
              AND state = ANY(%s)
              AND date < %s
              AND (location_id = %s OR location_dest_id = %s)
        """
        cr.execute(query_opening, (location.id, location.id, product.id, states, d_from, location.id, location.id))
        opening_qty = float(cr.fetchone()[0] or 0.0)

        # 2. Phát sinh trong kỳ
        query_moves = """
            SELECT
                sm.id AS move_id,
                sm.picking_id,
                sp.name AS picking_name,
                COALESCE(sm.origin, sp.origin, sm.reference) AS origin,
                sm.reference,
                sm.date,
                sm.state,
                sm.location_id,
                loc_src.complete_name AS loc_src_name,
                sm.location_dest_id,
                loc_dest.complete_name AS loc_dest_name,
                sm.product_uom_qty,
                sm.quantity,
                COALESCE(rp.name, ru_part.name) AS partner_name
            FROM stock_move sm
            LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
            LEFT JOIN res_partner rp ON rp.id = sp.partner_id
            LEFT JOIN mrp_production mrp ON (mrp.id = sm.raw_material_production_id OR mrp.id = sm.production_id)
            LEFT JOIN res_users ru ON ru.id = mrp.user_id
            LEFT JOIN res_partner ru_part ON ru_part.id = ru.partner_id
            LEFT JOIN stock_location loc_src ON loc_src.id = sm.location_id
            LEFT JOIN stock_location loc_dest ON loc_dest.id = sm.location_dest_id
            WHERE sm.product_id = %s
              AND sm.state = ANY(%s)
              AND sm.date >= %s AND sm.date <= %s
              AND (sm.location_id = %s OR sm.location_dest_id = %s)
            ORDER BY sm.date ASC, sm.id ASC
        """
        cr.execute(query_moves, (product.id, states, d_from, d_to, location.id, location.id))
        raw_rows = cr.dictfetchall()

        running_balance = opening_qty
        total_in = 0.0
        total_out = 0.0
        movements = []

        for row in raw_rows:
            is_in = (row['location_dest_id'] == location.id)
            is_out = (row['location_id'] == location.id)
            qty = float(row['quantity'] or 0.0)

            if is_in and not is_out:
                qty_in = qty
                qty_out = 0.0
                running_balance += qty
                total_in += qty
            elif is_out and not is_in:
                qty_in = 0.0
                qty_out = qty
                running_balance -= qty
                total_out += qty
            else:
                # Internal within same location
                qty_in = qty
                qty_out = qty

            movements.append({
                'move_id': row['move_id'],
                'picking_id': row['picking_id'],
                'picking_name': row['picking_name'] or row['reference'],
                'origin': row['origin'] or '',
                'reference': row['reference'] or '',
                'date': str(row['date']) if row['date'] else None,
                'partner': row['partner_name'] or None,
                'location_src': row['loc_src_name'] or '',
                'location_dest': row['loc_dest_name'] or '',
                'product_uom_qty': float(row['product_uom_qty'] or 0.0),
                'quantity_done': qty,
                'qty_in': qty_in,
                'qty_out': qty_out,
                'balance': round(running_balance, 3),
                'state': row['state'],
            })

        return {
            'product_id': product.id,
            'product_name': product.display_name,
            'location_id': location.id,
            'location_name': location.complete_name,
            'date_from': d_from,
            'date_to': d_to,
            'opening_balance': round(opening_qty, 3),
            'closing_balance': round(running_balance, 3),
            'total_in': round(total_in, 3),
            'total_out': round(total_out, 3),
            'total_movements': len(movements),
            'movements': movements,
        }
