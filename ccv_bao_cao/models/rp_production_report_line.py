# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RpProductionReportLine(models.Model):
    _name = 'rp.production.report.line'
    _description = 'Dòng báo cáo sản lượng'
    _order = 'no, id'

    parent_id = fields.Many2one('rp.production.report', string="Phiếu",
                                ondelete='cascade', index=True)
    no = fields.Integer(string="STT")
    stock_date_receipt = fields.Date(string="Ngày dùng tồn")
    name = fields.Char(string="Mã tham chiếu")
    picking_type_id = fields.Many2one('stock.picking.type', string="Loại hoạt động")
    product_id = fields.Many2one('product.product', string="Sản phẩm")
    product_code = fields.Char(string="Mã sản phẩm")
    product_name = fields.Char(string="Tên sản phẩm")
    uom_id = fields.Many2one('uom.uom', string="ĐVT")
    quantity = fields.Float(string="Số lượng sản xuất", digits=(16, 3))
    user_id = fields.Many2one('res.users', string="Người phụ trách")

    def unlink(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.state != 'draft':
                raise UserError(_("Không thể xóa dòng khi phiếu đã gửi duyệt!"))
        return super().unlink()
