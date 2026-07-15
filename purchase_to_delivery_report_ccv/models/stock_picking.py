# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    weight_ccv_net = fields.Float(string='Số lượng cân CCV trừ bì', compute='_compute_net_weight', store=True, readonly=False, digits="Product Unit of Measure")
    weight_port_net = fields.Float(string='Số lượng cân Cảng trừ bì', compute='_compute_net_weight', store=True, readonly=False, digits="Product Unit of Measure")

    @api.depends('weight_ccv', 'weight_port', 'move_ids.product_id', 'move_ids.product_id.default_specification_id', 'move_ids.product_id.packaging_specification_id')
    def _compute_net_weight(self):
        for picking in self:
            net_ccv = picking.weight_ccv or 0.0
            net_port = picking.weight_port or 0.0
            
            if picking.move_ids:
                product = picking.move_ids[0].product_id
                bag_uom = product.default_specification_id
                tare_uom = product.packaging_specification_id
                
                if bag_uom and tare_uom:
                    bag_factor = bag_uom.factor if bag_uom.uom_type == 'smaller' else (1.0 / bag_uom.factor if bag_uom.uom_type == 'bigger' else 1.0)
                    tare_factor = tare_uom.factor if tare_uom.uom_type == 'smaller' else (1.0 / tare_uom.factor if tare_uom.uom_type == 'bigger' else 1.0)
                    
                    if tare_factor != 0:
                        tare_ccv = (net_ccv * bag_factor) / tare_factor
                        tare_port = (net_port * bag_factor) / tare_factor
                        net_ccv -= tare_ccv
                        net_port -= tare_port

            picking.weight_ccv_net = net_ccv
            picking.weight_port_net = net_port
    def action_open_picking_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Phiếu kho',
            'res_model': 'stock.picking',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

class StockMove(models.Model):
    _inherit = 'stock.move'

    bag_number_adjust = fields.Float(string="Số bao điều chỉnh")

    @api.depends("bag_number_adjust")
    def compute_bag_number(self):
        super(StockMove, self).compute_bag_number()
        for move in self:
            if move.bag_number_adjust:
                move.bag_number = move.bag_number_adjust
