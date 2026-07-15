# -*- coding: utf-8 -*-
from odoo import api, fields, models


ITEM_TYPE_SELECTION = [
    ('hang_hoa', 'Hàng Hóa'),
    ('ghi_chu', 'Ghi chú'),
    ('chiet_khau', 'Chiết khấu'),
    ('bang_ke', 'Bảng kê'),
    ('phi_khac', 'Phí khác'),
]


class ViettelSinvoiceItemTypeSet(models.Model):
    _name = 'viettel.sinvoice.item.type.set'
    _description = 'Viettel S-Invoice Item Type Set'
    _order = 'is_default desc, id desc'

    name = fields.Char("Tên", required=True)
    active = fields.Boolean(default=True)
    is_default = fields.Boolean(string='Default')
    line_ids = fields.One2many('viettel.sinvoice.item.type.set.line', 'set_id', string='Lines')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._reset_other_defaults()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'is_default' in vals:
            self._reset_other_defaults()
        return res

    def _reset_other_defaults(self):
        default_records = self.filtered(lambda rec: rec.is_default)
        if default_records:
            latest_default = default_records.sorted(key=lambda rec: rec.id, reverse=True)[:1]
            (self.search([('id', 'not in', latest_default.ids), ('is_default', '=', True)])).write({'is_default': False})

    def get_mapping_dict(self):
        self.ensure_one()
        mapping = {}
        for line in self.line_ids.sorted('sequence'):
            mapping[line.item_type] = line.key_value
        return mapping


class ViettelSinvoiceItemTypeSetLine(models.Model):
    _name = 'viettel.sinvoice.item.type.set.line'
    _description = 'Viettel S-Invoice Item Type Set Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    set_id = fields.Many2one('viettel.sinvoice.item.type.set', required=True, ondelete='cascade')
    name = fields.Char("Tên", required=True)
    item_type = fields.Selection(string="Loại mặt hàng", selection=ITEM_TYPE_SELECTION, required=True)
    key_value = fields.Char(string='Khoá', required=True)
