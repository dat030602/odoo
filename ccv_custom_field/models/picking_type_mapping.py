# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PickingTypeMapping(models.Model):
    _name = 'picking.type.mapping'
    _description = 'Cấu hình ánh xạ Loại hoạt động'
    _rec_name = 'display_name'

    warehouse_id = fields.Many2one('stock.warehouse', string='Kho')
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    partner_ids = fields.Many2many('res.partner', string='Liên hệ')
    picking_type_id = fields.Many2one('stock.picking.type', string='Loại hoạt động')
    
    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('warehouse_id', 'product_id', 'partner_ids', 'picking_type_id')
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.warehouse_id:
                parts.append(rec.warehouse_id.name)
            if rec.product_id:
                parts.append(f"SP: {rec.product_id.display_name}")
            if rec.partner_ids:
                parts.append(f"LH: {len(rec.partner_ids)} đối tác")
            
            main_name = ' | '.join(parts) if parts else 'Cấu hình mới'
            picking_type_name = rec.picking_type_id.name if rec.picking_type_id else 'Chưa chọn loại hoạt động'

            rec.display_name = f"{main_name} -> {picking_type_name}"
