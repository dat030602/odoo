# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AlphaReportLine6(models.TransientModel):
    _name = 'alpha.report.line6'
    _description = 'Báo cáo số dư ngân hàng'

    parent_id = fields.Many2one('alpha.report', string="Thông tin chung")
    date = fields.Date()
    partner_id = fields.Many2one("res.partner", string="Khách hàng")
    account_id = fields.Many2one("account.account")
    number_bank = fields.Char(string="Tài khoản ngân hàng")
    name_bank = fields.Char(string="Tên ngân hàng")
    branch_bank = fields.Char(string="Chi nhánh ngân hàng")
    end_debit = fields.Float(string="Nợ cuối kỳ nguyên tệ", digits=(16, 2))
    total = fields.Float(string="Nợ cuối kỳ", digits=(16, 0))
    # Khu vực hóa đơn
    move_id = fields.Many2one("account.move", string="Số chứng từ")
    reference = fields.Char(string="Mã/Số hoá đơn")
    note = fields.Char(string="Diễn giải")
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


