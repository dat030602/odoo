# -*- coding: utf-8 -*-

from odoo import fields, models


class TrpApproveHistory(models.Model):
    _inherit = 'trp.approve.history'

    ccv_chi_tiet_cong_no_phai_thu_id = fields.Many2one(
        'ccv.chi.tiet.cong.no.phai.thu',
        string='Phiếu Chi tiết công nợ phải thu')
    ccv_tong_hop_cong_no_phai_thu_id = fields.Many2one(
        'ccv.tong.hop.cong.no.phai.thu',
        string='Phiếu Tổng hợp công nợ phải thu')
    ccv_so_chi_tiet_ke_toan_quy_tien_mat_id = fields.Many2one(
        'ccv.so.chi.tiet.ke.toan.quy.tien.mat',
        string='Sổ kế toán chi tiết quỹ tiền mặt')
