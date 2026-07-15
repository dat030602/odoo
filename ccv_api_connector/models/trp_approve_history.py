# -*- coding: utf-8 -*-

from odoo import fields, models


class TrpApproveHistory(models.Model):
    _inherit = 'trp.approve.history'

    rp_san_luong_nhap_xuat_id = fields.Many2one(
        'rp.san.luong.nhap.xuat',
        string='Báo cáo sản lượng nhập xuất')
    rp_san_luong_nhap_xuat_bocxep_id = fields.Many2one(
        'rp.san.luong.nhap.xuat.bocxep',
        string='Báo cáo tiền công bốc xếp')
