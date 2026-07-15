# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_create_orderpoint_wizard(self):
        """Mở wizard tạo orderpoint cho product.product"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo cảnh báo tồn kho',
            'res_model': 'create.orderpoint.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'active_model': 'product.product',
            },
        }
