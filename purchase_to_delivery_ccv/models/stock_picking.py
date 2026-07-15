# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    container_number = fields.Char(string='Container Number', help='Container number for this delivery order')
    weight_receipt = fields.Float(string='Số lượng chứng từ', digits="Product Unit of Measure", compute="_compute_weight_receipt")
    weight_ccv = fields.Float(string='Weight CCV', digits="Product Unit of Measure")
    weight_port = fields.Float(string='Weight Port', digits="Product Unit of Measure",)
    seal_number = fields.Char(string='Seal Number', help='Seal number for the container (from OCR)')
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        help='The purchase order this delivery was created from.',
    )
    stock_input_id = fields.Many2one('purchase.order.stock.input')
    bag_number = fields.Integer(
        string='Bag Number',
        compute='_compute_weight_receipt',
        store=False,
    )     # Custom field of ccv

    @api.depends('move_ids.quantity_done', 'move_ids.bag_number')
    def _compute_weight_receipt(self):
        for picking in self:
            picking.weight_receipt = sum(picking.move_ids.mapped('quantity_done'))
            picking.bag_number = sum(picking.move_ids.mapped('bag_number'))
    
    @api.onchange('container_number','seal_number')
    def _onchange_container_number_seal_number(self):
        for rec in self:
            if rec.container_number and rec.seal_number:
                po_id = self.env['purchase.order.stock.input'].search([('container_number','=',rec.container_number),('seal_number','=',rec.seal_number)],limit=1)
                rec.purchase_order_id = po_id.order_id


# class StockMove(models.Model):
#     _inherit = 'stock.move'

#     bag_number = fields.Integer(string='Bag Number')  # Custom field of ccv
