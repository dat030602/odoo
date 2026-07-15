from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

class CheckRequestAPI(models.TransientModel):
    _name = 'check.request.api.wizard'

    Id = fields.Char(string="ID")
    Stt = fields.Integer(string="STT")
    SoPhieu = fields.Char(string="Số phiếu")
    PhuongTien = fields.Char(string="Phương tiện")
    KhachHang = fields.Char(string="Khách hàng")
    SanPham = fields.Char(string="Sản phẩm")
    Idnm = fields.Char(string="ID nhà máy")
    IdCan = fields.Char(string="ID máy cân")
    Factory = fields.Many2one('npk.weighing.factory', string="Nhà máy")
    Machine = fields.Many2one('npk.weighing.machine', string="Máy cân")
    SLBatDau = fields.Integer(string="Số lượng bắt đầu")
    PlanCounter = fields.Integer(string="Số lượng kế hoạch")
    Counter = fields.Integer(string="Số lượng")
    Total = fields.Float(string="Tổng")
    CreateTime = fields.Datetime(string="Thời gian tạo")
    StartTime = fields.Datetime(string="Thời gian bắt đầu")
    StopTime = fields.Datetime(string="Thời gian dừng")
    LastTime = fields.Datetime(string="Thời gian cuối")
    Solo = fields.Char(string="Số lô")
    DonGia = fields.Float(string="Đơn giá")
    GhiChu = fields.Text(string="Ghi chú")
    IsFinished = fields.Boolean(string="Đã hoàn thành")
    IsDeleted = fields.Boolean(string="Đã xóa")

    @api.onchange('Idnm')
    def _onchange_Idnm(self):
        factory = self.env['npk.weighing.factory'].search([('code', '=', self.Idnm)], limit=1)
        if factory:
            self.Factory = factory
        else:
            self.Factory = False

    @api.onchange('IdCan')
    def _onchange_IdCan(self):
        machine = self.env['npk.weighing.machine'].search([('code', '=', self.IdCan)], limit=1)
        if machine:
            self.Machine = machine
        else:
            self.Machine = False