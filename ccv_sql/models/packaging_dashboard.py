from odoo import models, fields, api

class PackagingDashboard(models.AbstractModel):
    _name = 'ccv.packaging.dashboard'
    _description = 'Packaging Minimum Quantity Dashboard Data'

    @api.model
    def get_data(self):
        # Lấy các orderpoint của sản phẩm có mã bắt đầu bằng BB.
        orderpoints = self.env['stock.warehouse.orderpoint'].search([
            ('product_id.default_code', '=like', 'BB.%')
        ])

        total_packaging_count = len(orderpoints)
        below_min_count = 0
        items_below_min = []

        for op in orderpoints:
            # qty_on_hand là field compute trên stock.warehouse.orderpoint trong Odoo 16
            qty_on_hand = op.qty_on_hand
            min_qty = op.product_min_qty
            
            if qty_on_hand < min_qty:
                below_min_count += 1
                missing_qty = min_qty - qty_on_hand
                missing_percent = (missing_qty / min_qty * 100) if min_qty > 0 else 100

                items_below_min.append({
                    'id': op.product_id.id,
                    'op_id': op.id,
                    'code': op.product_id.default_code,
                    'name': op.product_id.name,
                    'display_name': f"[{op.product_id.default_code}] {op.product_id.name}",
                    'min_qty': min_qty,
                    'qty_on_hand': qty_on_hand,
                    'missing_qty': missing_qty,
                    'missing_percent': round(missing_percent, 2),
                })

        # Sắp xếp danh sách thiếu hụt giảm dần theo số lượng thiếu hụt tuyệt đối để vẽ top 10
        items_below_min = sorted(items_below_min, key=lambda x: x['missing_qty'], reverse=True)

        return {
            'total_count': total_packaging_count,
            'below_min_count': below_min_count,
            'safe_count': total_packaging_count - below_min_count,
            'items_below_min': items_below_min,
        }
