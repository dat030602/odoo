# -*- coding: utf-8 -*-
from odoo import models, api, _

class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    def action_recommend_packaging(self):
        # Find category "Đề xuất - Đặt bao bì"
        category = self.env['approval.category'].search([('name', 'ilike', 'Đề xuất - Đặt bao bì')], limit=1)
        if not category:
            category = self.env['approval.category'].search([], limit=1)

        product_lines = []
        for rec in self:
            if rec.product_id:
                product_lines.append((0, 0, {
                    'product_id': rec.product_id.id,
                    'quantity': rec.qty_to_order if rec.qty_to_order > 0 else 1.0,
                }))
        
        return {
            'name': 'Đề xuất - Đặt bao bì',
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
            'context': {
                'default_category_id': category.id if category else False,
                'default_product_line_ids': product_lines,
                'default_name': _('New') if category and category.automated_sequence else (category.name if category else ''),
            }
        }
