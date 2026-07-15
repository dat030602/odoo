# -*- coding: utf-8 -*-

from odoo import models, fields


class TrpApproveConfigLine(models.Model):
    _inherit = 'trp.approve.config.line'

    manager_type = fields.Selection(selection_add=[
        ('voter', 'Người lập phiếu'),
        ('warehouse_manager', 'Thủ Kho/Nhà Máy'),
        ('stock_controller', 'Chuyên viên kiểm soát kho'),
        ('supervisor', 'Giám sát'),
        ('receiver', 'Người nhận'),
        ('chief_acc', 'Phòng kế toán'),
        ('hcns', 'Phòng HCNS'),
        ('unit_heads', 'Thủ trưởng đơn vị'),
    ])
