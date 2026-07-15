# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleAuditDashboard(models.TransientModel):
    _name = 'sale.audit.dashboard'
    _description = 'Sales Audit Dashboard Backend'

    @api.model
    def get_dashboard_data(self, filters=None):
        if not filters:
            filters = {}

        domain = []
        if filters.get('date_from'):
            domain.append(('date_order', '>=', filters['date_from']))
        if filters.get('date_to'):
            domain.append(('date_order', '<=', filters['date_to']))
        if filters.get('team_id'):
            domain.append(('team_id', '=', int(filters['team_id'])))
        if filters.get('user_id'):
            domain.append(('user_id', '=', int(filters['user_id'])))

        sale_obj = self.env['sale.order']
        all_orders = sale_obj.search(domain)

        data = {
            'overview': {
                'total_orders': 0,
                'total_ordered_amount': 0.0,
                'total_delivered_amount': 0.0,
                'total_invoiced_amount': 0.0,
                'total_cancelled': 0,
            },
            'warehouse_alerts': {
                'qty_delivered_zero': 0,
                'price_unauthorized': 0,
                'svl_error': 0,
                'missing_picking': 0,
            },
            'operations': {
                'to_deliver': 0,
                'fully_delivered': 0,
                'to_invoice': 0,
                'returns': 0,
            }
        }

        # Check Price Edit Group (Skill Phân quyền)
        price_edit_group = self.env.ref('ccv_sale.group_allow_edit_price_sale_order', raise_if_not_found=False)
        authorized_users = price_edit_group.users.ids if price_edit_group else []

        for order in all_orders:
            # Overview
            data['overview']['total_orders'] += 1
            if order.state == 'cancel':
                data['overview']['total_cancelled'] += 1
            else:
                data['overview']['total_ordered_amount'] += order.amount_total
                
                delivered_ratio = 0.0
                invoiced_ratio = 0.0
                total_qty = sum(order.order_line.mapped('product_uom_qty'))
                if total_qty > 0:
                    delivered_ratio = sum(order.order_line.mapped('qty_delivered')) / total_qty
                    invoiced_ratio = sum(order.order_line.mapped('qty_invoiced')) / total_qty
                
                data['overview']['total_delivered_amount'] += order.amount_total * delivered_ratio
                data['overview']['total_invoiced_amount'] += order.amount_total * invoiced_ratio

                # Operations
                if order.invoice_status == 'to invoice':
                    data['operations']['to_invoice'] += 1

                pickings = order.picking_ids.filtered(lambda p: p.state != 'cancel')
                if pickings:
                    if all(p.state == 'done' for p in pickings):
                        data['operations']['fully_delivered'] += 1
                    else:
                        data['operations']['to_deliver'] += 1

                    if any(p.picking_type_code == 'incoming' for p in pickings):
                        data['operations']['returns'] += 1

                    done_outgoing = pickings.filtered(lambda p: p.state == 'done' and p.picking_type_code == 'outgoing')
                    if done_outgoing and sum(order.order_line.mapped('qty_delivered')) == 0:
                        data['warehouse_alerts']['qty_delivered_zero'] += 1
                else:
                    if order.state in ('sale', 'done'):
                        data['warehouse_alerts']['missing_picking'] += 1
                        data['operations']['to_deliver'] += 1

                if order.user_id and order.user_id.id not in authorized_users:
                    for line in order.order_line:
                        if line.product_id and line.price_unit != line.product_id.lst_price:
                            data['warehouse_alerts']['price_unauthorized'] += 1
                            break

        return data
