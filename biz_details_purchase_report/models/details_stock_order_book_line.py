# -*- coding: utf-8 -*-
from odoo import models, fields, api

class DetailsStockOrderBookLine(models.Model):
    _name = 'details.stock.order.book.line'
    _description = 'Chi tiết báo cáo hàng tồn kho khu vực'
    _order = 'product_id,date_proc desc'

    name = fields.Char(string="Tên", readonly=True)
    product_id = fields.Many2one('product.product', string="Sản phẩm", readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string="ĐVT", related="product_id.uom_id", readonly=True)
    quantity = fields.Float(string="Số lượng", digits=(16, 3), copy=False, readonly=True)
    order_id = fields.Many2one('sale.order', string="Đơn hàng", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Khách hàng", readonly=True)
    team_id = fields.Many2one('crm.team', string="Khu vực", readonly=True)
    team_name = fields.Char(string="Khu vực", compute="_compute_team_id", readonly=True)
    date_proc = fields.Date(string="Ngày sản xuất", readonly=True)
    picking_type_id = fields.Many2one('stock.picking.type', string="Nhà máy sản xuất", readonly=True)
    factory_name = fields.Char(string="Nhà máy sản xuất", compute="_compute_picking_type_id", readonly=True)
    note = fields.Char(string="Ghi Chú")
    
    parent_id = fields.Many2one('details.stock.order.book', ondelete='cascade')
    
    @api.depends('picking_type_id')
    def _compute_picking_type_id(self):
        for rec in self:
            rec.factory_name = rec.picking_type_id.factory_name if hasattr(rec.picking_type_id, 'factory_name') else ''
            
    @api.depends('team_id')
    def _compute_team_id(self):
        for rec in self:
            rec.team_name = rec.team_id.report_name if hasattr(rec.team_id, 'report_name') else rec.team_id.name
