# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AlphaReportLine4(models.TransientModel):
    _name = 'alpha.report.line4'
    _description = 'Sổ kế toán chi tiết quỹ tiền mặt'

    parent_id = fields.Many2one('alpha.report', string="Thông tin chung")
    date = fields.Date()
    partner_id = fields.Many2one("res.partner", string="Khách hàng")
    partner_ids = fields.Many2many("res.partner", string="Khách hàng / Đối tác")
    product_tmpl_id = fields.Many2one("product.template", string="Sản phẩm")
    product_id = fields.Many2one("product.product", string="Sản phẩm")
    product_uom_qty = fields.Float("Số lượng")
    product_uom_id = fields.Many2one("uom.uom", string="Đvt", related="product_id.uom_id")
    default_code = fields.Char(string="Mã hàng")
    uom_id = fields.Many2one("uom.uom", string="Đvt")
    price_unit = fields.Float('Đơn giá')
    price_subtotal = fields.Float('Đơn giá trước thuế')
    price_tax = fields.Float("Đơn giá thuế")
    amount_untaxed = fields.Float("Tiền chưa thuế", digits=(16, 0))
    amount_tax = fields.Float("Tiền thuế", digits=(16, 0))
    amount_total = fields.Float("Tổng tiền", related=False, digits=(16, 0))
    amount_payment = fields.Float("Đã thanh toán", digits=(16, 0))
    residual = fields.Float("Còn lại", digits=(16, 0))
    invoice_name = fields.Char(string="Hóa đơn")
    account_id = fields.Many2one("account.account", string="Tài khoản")
    account_dest_id = fields.Many2one("account.account", string="Tài khoản")
    start_debit = fields.Float(string="Nợ đầu kỳ", digits=(16, 0))
    start_credit = fields.Float(string="Có đầu kỳ", digits=(16, 0))
    debit = fields.Float(string="PS nợ", digits=(16, 0))
    credit = fields.Float(string="PS có", digits=(16, 0))
    end_debit = fields.Float(string="Nợ cuối kỳ", digits=(16, 0))
    end_credit = fields.Float(string="Có cuối kỳ", digits=(16, 0))
    # Khu vực hóa đơn
    move_id = fields.Many2one("account.move", string="Số chứng từ")
    move2_id = fields.Many2one("account.move")
    reference = fields.Char(string="Mã/Số hoá đơn")
    note = fields.Char(string="Diễn giải")
    state_invoice = fields.Selection(related="move_id.state", string="Trạng thái")
    level = fields.Integer()
    move_type = fields.Selection(
        selection=[
            ('entry', 'Journal Entry'),
            ('out_invoice', 'HĐ ra'),
            ('out_refund', 'Customer Credit Note'),
            ('in_invoice', 'HĐ vào'),
            ('in_refund', 'Vendor Credit Note'),
            ('out_receipt', 'Sales Receipt'),
            ('in_receipt', 'Purchase Receipt'),
        ],
        string='Loại',
    )
    employee_id = fields.Many2one("hr.employee", string="Nhân viên")
    employee_code = fields.Char(string="Mã nhân viên")
    partner_code = fields.Char(string="Mã NCC")
    partner_type = fields.Selection(related="parent_id.partner_type", store=True)

    def view_detail(self):
        stock_move_ids = self.env['stock.move'].search([('product_id', '=', self.product_id.id)])
        for line in stock_move_ids:
            self.create({
                'name': self.product_name,
                'location_id': line.location_id.id,
                'location_dest_id': line.location_dest_id.id,
                'product_uom_qty': line.quantity_done,
                'partner_id': self.partner_id.id,
                'barcode': self.barcode,
                'user_id': self.user_id.id,
                'state_stock_move': line.state,
                'agency_id': self.agency_id.id,
                'stock_move_id': line.id,
                'report_line_id': self.id,
            })
        return {
            'name': "Xem chi tiết",
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'alpha.report.line',
            'view_id': self.env.ref('alpha_sql.view_detail_tree_tracking_product_report_view').id,
            'domain': [],
        }

    def action_view_tree_line(self):
        name = ''
        view_id = False
        if self.parent_id.type == 'bao_cao_nhap_xuat_ton':
            self.chi_tiet_nhap_xuat_ton()
            name = "Xem chi tiết " + self.product_tmpl_id.name
            view_id = self.env.ref('alpha_sql.chi_tiet_nhap_xuat_ton').id
        if self.parent_id.type == 'account':
            self.chi_tiet_cong_no_phai_tra()
            view_id = self.env.ref('alpha_sql.tree_alpha_report_line_view_for_chi_tiet_cong_no_phai_tra').id
            if self.account_id:
                name = "Tài khoản: %s, Đối tượng %s" % (self.account_id.name_get()[0][1], self.partner_id.name_get()[0][1])
            else:
                name = "Tài khoản: %s" % (self.partner_id.name_get()[0][1])
        if self.parent_id.type == 'bao_cao_doanh_thu_gia_von_theo_don_hang':
            self.chi_tiet_bao_cao_doanh_thu_gia_von_theo_don_hang()
            view_id = self.env.ref('alpha_sql.tree_alpha_report_line_view_for_bao_cao_doanh_thu_gia_von_theo_don_hang').id
            name = "Chi tiết doanh thu gia vốn"
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'alpha.report.line',
            'view_id': view_id,
            'domain': [('level', '=', 2)],
        }


