# -*- coding: utf-8 -*-

from odoo import fields, models


class TrpApproveHistory(models.Model):
    _inherit = 'trp.approve.history'

    material_detail_book_id = fields.Many2one(
        'material.detail.book',
        string='Sổ chi tiết vật tư')

    mrp_production_id = fields.Many2one(
        'mrp.production',
        string='Lệnh sản xuất')
