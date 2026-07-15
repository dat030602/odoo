# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CreateOrderpointWizard(models.TransientModel):
    _name = 'create.orderpoint.wizard'
    _description = 'Wizard tạo Orderpoint'

    warehouse_id = fields.Many2one('stock.warehouse', string='Kho', required=True)
    product_min_qty = fields.Float(string='Số lượng tối thiểu', required=True, default=0.0, digits='Product Unit of Measure')
    product_max_qty = fields.Float(string='Số lượng tối đa', required=True, default=0.0, digits='Product Unit of Measure')
    product_ids = fields.Many2many('product.product', string='Sản phẩm')

    @api.model
    def default_get(self, fields_list):
        res = super(CreateOrderpointWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', '')
        
        if active_model in ['product.template', 'product.product']:
            if active_model == 'product.template':
                products = self.env['product.product'].search([('product_tmpl_id', 'in', active_ids)])
            else:
                products = self.env['product.product'].browse(active_ids)
            
            res['product_ids'] = [(6, 0, products.ids)]
        
        return res

    def action_create_orderpoint(self):
        """Tạo stock.warehouse.orderpoint cho các sản phẩm được chọn"""
        if not self.product_ids:
            raise ValidationError(_('Vui lòng chọn ít nhất một sản phẩm!'))
        
        if self.product_min_qty < 0 or self.product_max_qty < 0:
            raise ValidationError(_('Số lượng không được âm!'))
        
        if self.product_max_qty < self.product_min_qty and self.product_max_qty != 0 and self.product_min_qty != 0:
            raise ValidationError(_('Số lượng tối đa phải lớn hơn hoặc bằng số lượng tối thiểu!'))
        
        orderpoint_vals = []
        for product in self.product_ids:
            # Kiểm tra xem đã có orderpoint cho sản phẩm và kho này chưa
            existing_orderpoint = self.env['stock.warehouse.orderpoint'].sudo().search([
                ('product_id', '=', product.id),
                ('warehouse_id', '=', self.warehouse_id.id)
            ], limit=1)
            
            if existing_orderpoint:
                # Cập nhật orderpoint hiện có
                existing_orderpoint.write({
                    'product_min_qty': self.product_min_qty,
                    'product_max_qty': self.product_max_qty,
                    'trigger': 'manual',
                })
            else:
                # Tạo orderpoint mới
                orderpoint_vals.append({
                    'name': f'Orderpoint {product.name} - {self.warehouse_id.name}',
                    'product_id': product.id,
                    'warehouse_id': self.warehouse_id.id,
                    'location_id': self.warehouse_id.lot_stock_id.id,
                    'product_min_qty': self.product_min_qty,
                    'product_max_qty': self.product_max_qty,
                    'product_category_id': product.categ_id.id,
                    'trigger': 'manual',
                })
        
        if orderpoint_vals:
            self.env['stock.warehouse.orderpoint'].sudo().create(orderpoint_vals)
        
        return {
            'type': 'ir.actions.act_window_close',
        }
