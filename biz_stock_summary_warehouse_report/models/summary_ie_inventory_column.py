# -*- coding: utf-8 -*-
from odoo import fields, models

class SummaryIEInventoryColumn(models.Model):
    _name = 'summary.ie.inventory.column'
    _description = 'Summary IE Inventory Column'
    _order = 'sequence, id'

    summary_id = fields.Many2one('summary.ie.inventory', string='Summary', required=True, ondelete='cascade')
    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    is_visible = fields.Boolean('Hiển thị', default=True)
    sequence = fields.Integer('Sequence', default=10)

    _sql_constraints = [
        ('summary_ie_inventory_column_unique', 'unique(summary_id, code)', 'Column code must be unique per summary.'),
    ]