from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class WzInvoiceDataCreateInvoice(models.TransientModel):
    _name = 'wz.invoice.data.create.invoice'
    _description = 'Tạo hóa đơn nhà cung cấp từ dữ liệu hóa đơn'

    invoice_data_id = fields.Many2one('invoice.data', string='Dữ liệu hóa đơn')
    order_line = fields.One2many('wz.invoice.data.create.invoice.line', 'wizard_id', string='Danh sách sản phẩm')

    def action_confirm(self):
        """Xác nhận tạo hóa đơn"""
        lines = self.order_line.filtered(lambda x: x.is_selected)
        if not lines:
            raise ValidationError(_("Vui lòng chọn sản phẩm để tạo hóa đơn"))

        _logger.info(f"Tạo hóa đơn với {len(lines)} dòng được chọn")

        self.invoice_data_id.create_data_mapping_product()

        return self.invoice_data_id.action_done_create_invoice(lines)


class WzInvoiceDataCreateInvoiceLine(models.TransientModel):
    _name = 'wz.invoice.data.create.invoice.line'
    _description = 'Dòng sản phẩm trong wizard tạo hóa đơn'

    wizard_id = fields.Many2one('wz.invoice.data.create.invoice', ondelete='cascade')
    invoice_data_line_id = fields.Many2one('invoice.data.line.m2o', string='Dòng dữ liệu')
    is_selected = fields.Boolean('Được chọn', default=True)

    # Các trường hiển thị từ dòng dữ liệu
    sequence = fields.Integer('Thứ tự')
    product_id = fields.Many2one('product.product', 'Sản phẩm')
    purchase_line_id = fields.Many2one('purchase.order.line', 'Đơn đặt hàng')
    uom_id = fields.Many2one('uom.uom', 'Đơn vị tính')
    account_id = fields.Many2one('account.account', 'Tài khoản')
    so_luong = fields.Float('Số lượng')
    don_gia = fields.Float('Đơn giá')
    thanh_tien = fields.Float('Thành tiền')
    tax_id = fields.Many2one('account.tax', 'Thuế suất')
    thue_gtgt = fields.Float('Thuế GTGT')
    ghi_chu = fields.Text('Ghi chú')
