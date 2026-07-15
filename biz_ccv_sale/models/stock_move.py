# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    description = fields.Char('Description')
    bag_number = fields.Integer('Bag number',readonly=True, compute="compute_bag_number", store=True)
    stt = fields.Integer('STT',compute="_compute_stt",store=True)
    product_uom_qty_float = fields.Char('Product Uom Qty Float Docx',compute="_compute_product_uom_qty_float",store=True)
    product_image = fields.Binary(string="Product Image", compute='compute_get_image',
                                  help="Small-sized image of the product.")
    bag_done = fields.Integer("Done bag number")
    packaging_image = fields.Binary(string="Packaging Image", copy=False, related="product_id.packaging_image")

    @api.depends('product_id')
    def compute_get_image(self):
        for record in self:
            product_image = None
            if record.product_id and record.product_id.image_1024:
                product_image = record.product_id.image_1024
            record.product_image = product_image

    @api.depends('product_uom_qty')
    def _compute_product_uom_qty_float(self):
        for res in self:
            res.product_uom_qty_float = '0'
            if res.product_uom_qty:
                total = res.product_uom_qty
                if total != 0:
                    total = str('{:,.3f}'.format(total)).replace(".", ",")
                    res.product_uom_qty_float = total

    @api.depends('picking_id')
    def _compute_stt(self):
        for res in self:
            search_stt = self.search([('picking_id','=',res.picking_id.id)])
            stt = 1
            res.stt = 0
            for se in search_stt:
                if se.id == res.id:
                    res.stt = stt
                stt += 1

    @api.model_create_multi
    def create(self,vals):
        result = super(StockMove,self).create(vals)
        for res in result:
            if res.sale_line_id:
                res.description = res.description_picking
        return result

    @api.depends("product_id",'product_uom','product_uom_qty', 'quantity_done', 'picking_id.state')
    def compute_bag_number(self):
        for res in self:
            bag_number = 0
            quantity = res.product_uom_qty
            if res.picking_id.state == 'assigned' and res.quantity_done:
                quantity = res.quantity_done
            elif res.picking_id.state == 'done':
                quantity = res.quantity_done

            default_specification_id = res.product_id.default_specification_id
            if default_specification_id:
                if default_specification_id.uom_type == 'reference':
                    if res.product_uom and res.product_uom.uom_type == 'smaller':
                        bag_number = quantity / res.product_uom.factor
                    if res.product_uom and res.product_uom.uom_type == 'bigger':
                        bag_number = quantity * res.product_uom.factor
                if default_specification_id.uom_type == 'smaller':
                    if res.product_uom and res.product_uom.uom_type == 'reference':
                        bag_number = quantity * default_specification_id.factor
                    if res.product_uom and res.product_uom.uom_type == 'bigger':
                        bag_number = (quantity / res.product_uom.factor)*default_specification_id.factor
                if default_specification_id.uom_type == 'bigger':
                    if res.product_uom and res.product_uom.uom_type == 'reference':
                        bag_number = quantity / default_specification_id.factor
                    if res.product_uom and res.product_uom.uom_type == 'smaller':
                        bag_number = (quantity * res.product_uom.factor)/default_specification_id.factor

            res.bag_number = bag_number

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    product_image = fields.Binary(string="Product Image", compute='compute_get_image',
                                  help="Small-sized image of the product.")

    packaging_image = fields.Binary(string="Packaging Image", copy=False, related="product_id.packaging_image")
    
    @api.depends('product_id')
    def compute_get_image(self):
        for record in self:
            product_image = None
            if record.product_id and record.product_id.image_1024:
                product_image = record.product_id.image_1024
            record.product_image = product_image

