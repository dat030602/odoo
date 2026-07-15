# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError


class RpThuTienReportLine(models.Model):
    _name = 'rp.thu.tien.report.line'
    _description = 'Dòng báo cáo thu tiền PKD'
    _order = 'no, id'

    parent_id = fields.Many2one('rp.thu.tien.report', string="Phiếu",
                                ondelete='cascade', index=True)
    no = fields.Integer(string="STT")
    date = fields.Date(string="Ngày")
    partner_id = fields.Many2one('res.partner', string="Khách hàng")
    partner_code = fields.Char(string="Mã khách hàng")
    partner_name = fields.Char(string="Tên khách hàng")
    reference = fields.Char(string="Mã phiếu")
    note = fields.Char(string="Số")
    amount = fields.Monetary(string="Số tiền thanh toán", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Tiền tệ")
    payment_id = fields.Many2one('account.payment', string="Phiếu thu")
    move_id = fields.Many2one('account.move', string="Bút toán")
    pkd_sign = fields.Char(string="PKD ký xác nhận")

    def unlink(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.state != 'draft':
                raise UserError(_("Không thể xóa dòng khi phiếu đã gửi duyệt!"))
        return super().unlink()
