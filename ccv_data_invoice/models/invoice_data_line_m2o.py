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


class InvoiceDataMisaLineM2O(models.Model):
    _name = 'invoice.data.line.m2o'
    _description = 'Dòng hàng hóa dịch vụ hóa đơn (M2O)'
    _order = 'sequence, id'
    
    sequence = fields.Integer(string='Thứ tự', default=10)
    invoice_id = fields.Many2one('invoice.data', string='Hóa đơn', required=True, ondelete='cascade')
    
    # Thông tin hàng hóa dịch vụ với trường m2o
    product_id = fields.Many2one('product.product', string='Tên hàng hóa dịch vụ')
    product_name = fields.Char(string='Tên trong HĐ')
    uom_id = fields.Many2one('uom.uom', string='Đơn vị tính')
    account_id = fields.Many2one('account.account', string='Tài khoản')
    so_luong = fields.Float(string='Số lượng', default=1.0, digits=(16, 3))
    don_gia = fields.Float(string='Đơn giá', digits=(16, 2))
    thanh_tien = fields.Float(string='Thành tiền', digits=(16, 2))
    tax_id = fields.Many2one('account.tax', string='Thuế suất', domain="[('type_tax_use', '=', 'purchase')]")
    ghi_chu = fields.Text(string='Ghi chú')
    tong_tien = fields.Float(string='Tổng tiền', compute='_compute_tong_tien', store=True)
    currency_id = fields.Many2one('res.currency', string='Loại tiền tệ', related='invoice_id.currency_id', store=True, readonly=True)
    # Trường tính toán
    thue_gtgt = fields.Float(string='Thuế GTGT', compute='_compute_thue_gtgt', store=True)
    
    # Trường tham chiếu đến dòng gốc
    source_line_id = fields.Many2one('invoice.data.line', string='Dòng gốc', readonly=True)

    @api.depends('thanh_tien', 'thue_gtgt')
    def _compute_tong_tien(self):
        for record in self:
            record.tong_tien = record.thanh_tien + record.thue_gtgt
    
    @api.depends('thanh_tien', 'tax_id')
    def _compute_thue_gtgt(self):
        for record in self:
            if record.tax_id and record.thanh_tien:
                record.thue_gtgt = record.thanh_tien * (record.tax_id.amount / 100)
            else:
                record.thue_gtgt = 0.0
    
    @api.onchange('so_luong', 'don_gia')
    def _onchange_thanh_tien(self):
        """Tự động tính thành tiền khi thay đổi số lượng hoặc đơn giá"""
        for record in self:
            if record.so_luong and record.don_gia:
                record.thanh_tien = record.so_luong * record.don_gia
    
    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     """Tự động điền đơn vị tính khi chọn sản phẩm"""
    #     for record in self:
    #         if record.product_id:
    #             record.uom_id = record.product_id.uom_id
    #             record.account_id = record.product_id._get_product_accounts().get('expense', False).id if record.product_id._get_product_accounts().get('expense', False) else False
    
    @api.onchange('tax_id')
    def _onchange_tax_id(self):
        """Tự động tính lại thuế GTGT khi thay đổi thuế suất"""
        for record in self:
            if record.tax_id and record.thanh_tien:
                record.thue_gtgt = record.thanh_tien * (record.tax_id.amount / 100)
    
    def name_get(self):
        """Hiển thị tên dòng M2O"""
        result = []
        for record in self:
            name = f"{record.product_id.name}"
            if record.uom_id:
                name += f" ({record.uom_id.name})"
            if record.so_luong:
                name += f" - SL: {record.so_luong}"
            result.append((record.id, name))
        return result
