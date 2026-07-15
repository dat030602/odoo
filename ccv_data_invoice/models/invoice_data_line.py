from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import unidecode
from rapidfuzz import process
import logging

_logger = logging.getLogger(__name__)

def normalize_name(name):
    """Chuẩn hóa tên sản phẩm (lowercase, bỏ dấu, chuẩn ký tự phân cách)."""
    if not name:
        return ""
    name = name.lower()
    name = unidecode.unidecode(name)  # bỏ dấu
    name = re.sub(r'[\s\*xX\-]+', 'x', name)  # chuẩn hóa x/*/-
    name = re.sub(r'\s+', ' ', name).strip()
    return name

class InvoiceDataMisaLine(models.Model):
    _name = 'invoice.data.line'
    _description = 'Dòng hàng hóa dịch vụ hóa đơn'
    _order = 'sequence, id'
    
    sequence = fields.Integer(string='Thứ tự', default=10)
    invoice_id = fields.Many2one('invoice.data', string='Hóa đơn', required=True, ondelete='cascade')
    
    # Thông tin hàng hóa dịch vụ
    ten = fields.Char(string='Tên hàng hóa dịch vụ', required=True)
    dvt = fields.Char(string='Đơn vị tính')
    so_luong = fields.Float(string='Số lượng', default=1.0, digits=(16, 3))
    don_gia = fields.Float(string='Đơn giá', digits=(16, 2))
    thanh_tien = fields.Float(string='Thành tiền', digits=(16, 2))
    thue_suat = fields.Char(string='Thuế suất', default='0%')
    ghi_chu = fields.Text(string='Ghi chú')
    tong_tien = fields.Float(string='Tổng tiền', compute='_compute_tong_tien', store=True)
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', related='invoice_id.currency_id', store=True, readonly=True)
    
    # Trường tính toán
    thue_gtgt = fields.Float(string='Thuế GTGT', compute='_compute_thue_gtgt', store=True)

    @api.depends('thanh_tien', 'thue_gtgt')
    def _compute_tong_tien(self):
        for record in self:
            record.tong_tien = record.thanh_tien + record.thue_gtgt
    
    @api.depends('thanh_tien', 'thue_suat')
    def _compute_thue_gtgt(self):
        for record in self:
            try:
                if record.thue_suat and record.thanh_tien:
                    # Lấy phần trăm từ chuỗi (ví dụ: "10%" -> 10)
                    thue_suat_value = float(record.thue_suat.replace('%', ''))
                    record.thue_gtgt = record.thanh_tien * (thue_suat_value / 100)
                else:
                    record.thue_gtgt = 0.0
            except (ValueError, AttributeError):
                record.thue_gtgt = 0.0
    
    @api.onchange('so_luong', 'don_gia')
    def _onchange_thanh_tien(self):
        """Tự động tính thành tiền khi thay đổi số lượng hoặc đơn giá"""
        for record in self:
            if record.so_luong and record.don_gia:
                record.thanh_tien = record.so_luong * record.don_gia
