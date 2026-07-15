# -*- coding: utf-8 -*-

from odoo import models, fields


class CcvChiTietCongNoPhaiThuLine(models.Model):
    _name = 'ccv.chi.tiet.cong.no.phai.thu.line'
    _description = 'Chi tiết công nợ phải thu (dòng phiếu duyệt)'

    _order = 'sequence, id'

    parent_id = fields.Many2one('ccv.chi.tiet.cong.no.phai.thu', string="Phiếu", ondelete='cascade', index=True)
    sequence = fields.Integer(string="Thứ tự", default=10)
    team_id = fields.Many2one('crm.team', string="Đội bán hàng")
    date = fields.Date(string="Ngày chứng từ")
    partner_id = fields.Many2one("res.partner", string="Khách hàng")
    product_id = fields.Many2one("product.product", string="Sản phẩm")
    product_uom_qty = fields.Float(string="Số lượng")
    default_code = fields.Char(string="Mã hàng")
    uom_id = fields.Many2one("uom.uom", string="Đvt")
    price_unit = fields.Float(string="Đơn giá")
    amount_tax = fields.Float(string="Tiền thuế", digits=(16, 0))
    account_id = fields.Many2one("account.account", string="Tài khoản")
    account_dest_id = fields.Many2one("account.account", string="TK đối ứng")
    debit = fields.Float(string="PS nợ", digits=(16, 0))
    credit = fields.Float(string="PS có", digits=(16, 0))
    end_debit = fields.Float(string="SD nợ", digits=(16, 0))
    end_credit = fields.Float(string="SD có", digits=(16, 0))
    end_w_tax_debit = fields.Float(string="SD nợ (gồm thuế)", digits=(16, 0))
    end_w_tax_credit = fields.Float(string="SD có (gồm thuế)", digits=(16, 0))
    move_id = fields.Many2one("account.move", string="Số chứng từ")
    reference = fields.Char(string="Mã/Số hóa đơn")
    note = fields.Char(string="Diễn giải")
    order_id = fields.Many2one("sale.order", string="Mã đơn hàng")
    partner_code = fields.Char(string="Mã khách hàng")
    display_type = fields.Selection([
        ('product', 'Product'),
        ('cogs', 'Cost of Goods Sold'),
        ('tax', 'Tax'),
        ('rounding', "Rounding"),
        ('payment_term', 'Payment Term'),
        ('line_section', 'Section'),
        ('line_note', 'Note'),
        ('epd', 'Early Payment Discount'),
    ], string="Loại")
    level = fields.Integer()
    move_type = fields.Selection([
        ('entry', 'Journal Entry'),
        ('out_invoice', 'HĐ ra'),
        ('out_refund', 'Customer Credit Note'),
        ('in_invoice', 'HĐ vào'),
        ('in_refund', 'Vendor Credit Note'),
        ('out_receipt', 'Sales Receipt'),
        ('in_receipt', 'Purchase Receipt'),
    ], string='Loại HĐ')
