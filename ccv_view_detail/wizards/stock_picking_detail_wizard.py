from odoo import models, fields, api

class StockPickingDetailWizard(models.TransientModel):
    _name = 'stock.picking.detail.wizard'
    _description = 'Wizard Chi tiết đơn nhập hàng'

    picking_id = fields.Many2one('stock.picking', string='Phiếu kho', readonly=True)
    partner_id = fields.Many2one(related='picking_id.partner_id', readonly=True, string='Đối tác')
    stock_date_receipt = fields.Datetime(related='picking_id.stock_date_receipt', readonly=True, string='Ngày')
    origin = fields.Char(related='picking_id.origin', readonly=True, string='Nguồn gốc')
    location_id = fields.Many2one(related='picking_id.location_id', readonly=True, string='Kho xuất')
    location_dest_id = fields.Many2one(related='picking_id.location_dest_id', readonly=True, string='Kho nhập')
    picking_type_id = fields.Many2one(related='picking_id.picking_type_id', readonly=True, string='Loại phiếu kho')
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('waiting', 'Chờ hàng'),
        ('confirmed', 'Đã xác nhận'),
        ('assigned', 'Đã gán'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Đã hủy')
    ], string='Trạng thái', readonly=True, compute='_compute_state')
    move_ids = fields.One2many(related='picking_id.move_ids', readonly=True, string='Chi tiết sản phẩm')
    
    @api.depends('picking_id')
    def _compute_state(self):
        for record in self:
            if record.picking_id:
                record.state = record.picking_id.state
            else:
                record.state = False 
    