# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AddToPackingListWizardLine(models.TransientModel):
    _name = "add.to.packing.list.wizard.line"
    _description = 'Wizard Add to Packing list Line'

    name = fields.Text(string='Name')

    sequence = fields.Integer(string='Sequence')
    display_type = fields.Selection(string='Display Type',
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)

    add_order_id = fields.Many2one('add.to.packing.list.wizard')
    order_ids = fields.Many2many('sale.order', string="Order", related="add_order_id.order_ids")
    product_id = fields.Many2one('product.product', related="order_line_id.product_id", string='Product')
    order_line_ids = fields.Many2many('sale.order.line', string='Order Lines',compute='_compute_order_line_ids')
    store_order_line_ids = fields.Many2many('sale.order.line', string='Stored Order Lines',compute='_compute_store_order_line_ids')
    order_line_id = fields.Many2one('sale.order.line', string='SO Line')

    price_unit = fields.Float(string='Unit Price')
    product_uom_qty = fields.Float(string='Product UOM Quantity')
    price_subtotal = fields.Float(string='Price Subtotal')
    currency_id = fields.Many2one('res.currency', string='Currency')

    @api.depends('order_ids', 'order_line_id')
    def _compute_order_line_ids(self):
        for record in self:
            order_lines = record.order_ids.order_line.filtered(
                lambda sol: sol.display_type or sol.packable_remaining_qty > 0
            )
            record.order_line_ids = [(6, 0, order_lines.ids)]
    
    @api.depends('order_ids','order_line_id')
    def _compute_store_order_line_ids(self):
        for record in self:
            order_line_organize_ids = record.add_order_id.order_line_wizard_ids.mapped('order_line_id').ids
            record.store_order_line_ids = [(4, order_line_id) for order_line_id in order_line_organize_ids]

    @api.onchange('order_line_id')
    def _onchange_order_line_id(self):
        order_line = self.order_line_id
        order_line_disyplay_type = order_line.display_type
        if self.order_line_id and order_line_disyplay_type == False:
            self.name = order_line.name
            self.product_id = order_line.product_id.id
            self.price_unit = order_line.price_unit
            self.product_uom_qty = order_line.packable_remaining_qty
            self.price_subtotal = order_line.price_subtotal
            self.currency_id = order_line.currency_id
        elif self.order_line_id and order_line_disyplay_type != False:
            self.name = order_line.name
            self.display_type = order_line_disyplay_type