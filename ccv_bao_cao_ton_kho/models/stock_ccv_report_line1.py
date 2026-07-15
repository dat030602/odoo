from odoo import models, fields,api
import logging

_logger = logging.getLogger(__name__)

class StockReportLine1(models.Model):
    _name = "stock.ccv.report.line1"

    name = fields.Char(string="Tên")
    origin = fields.Char(string="Nguồn gốc")
    ref = fields.Char(string="Mã tham chiếu")
    date = fields.Datetime(string="Ngày")
    picking_id = fields.Many2one('stock.picking', string="Phiếu xuất")
    partner_id = fields.Many2one('res.partner', string="Khách hàng")
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    location_origin_id = fields.Many2one('stock.location', string="Vị trí gốc")
    location_id = fields.Many2one('stock.location', string="Vị trí nguồn")
    location_dest_id = fields.Many2one('stock.location', string="Vị trí đích")
    qty = fields.Float(string="Số lượng", digits=(16, 3))
    qty_done = fields.Float(string="Số lượng đã làm", digits=(16, 3))
    stock_quant_qty = fields.Float(string="Tồn kho", digits=(16, 3), default=0.000)
    from_qty_done = fields.Float(string="Số lượng xuất", compute="_compute_quantity",store=True)
    to_qty_done = fields.Float(string="Số lượng nhập", compute="_compute_quantity",store=True)
    state = fields.Selection(selection=[
        ("draft", "Mới"),
        ("cancel", "Đã hủy"),
        ("waiting", "Chờ dịch chuyển khác"),
        ("confirmed", "Chờ có hàng"),
        ("partially_available", "Có hàng một phần"),
        ("assigned", "Còn hàng"),
        ("done", "Hoàn tất"),
    ], string="Trạng thái")
    parent_id = fields.Many2one("stock.ccv.report", string="Báo cáo")

    is_in = fields.Char(compute="_compute_is_out")

    @api.depends("qty_done")
    def _compute_quantity(self):
        for rec in self:
            if rec.location_id == rec.location_origin_id:
                rec.from_qty_done = rec.qty_done
                rec.to_qty_done = 0
            else:
                rec.from_qty_done = 0
                rec.to_qty_done = rec.qty_done

    @api.depends('location_origin_id','location_dest_id')
    def _compute_is_out(self):
        for rec in self:
            rec.is_in = 'in' if rec.location_origin_id and rec.location_origin_id.id == rec.location_dest_id.id else 'out'

    def action_open_reference(self):
        self.ensure_one()
        if not self.picking_id and not self.ref:
            return {}
        action = {}
        if self.picking_id:
            action = {
                'res_model': "stock.picking",
                'type': 'ir.actions.act_window',
                'views': [[False, "form"]],
                'res_id': self.picking_id.id,
            }
        elif self.ref:
            picking_env = self.env['stock.picking'].sudo()
            mrp_env = self.env['mrp.production'].sudo()
            picking_id = picking_env.search([('name','=',self.ref)])
            mrp_id = mrp_env.search([('name','=',self.ref)])
            if picking_id:
                action = {
                    'res_model': "stock.picking",
                    'type': 'ir.actions.act_window',
                    'views': [[False, "form"]],
                    'res_id': picking_id.id,
                }
            elif mrp_id:
                action = {
                    'res_model': "mrp.production",
                    'type': 'ir.actions.act_window',
                    'views': [[False, "form"]],
                    'res_id': mrp_id.id,
                }
        return action
