from odoo import api, fields, models

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    readiness_percentage = fields.Float(compute='_compute_readiness', string='Readiness %')
    shortage_line_count = fields.Integer(compute='_compute_shortage_count', string='Shortage Count')

    @api.depends('move_raw_ids.product_uom_qty', 'move_raw_ids.quantity')
    def _compute_readiness(self):
        for mo in self:
            total_demand = sum(mo.move_raw_ids.mapped('product_uom_qty'))
            if total_demand > 0:
                total_reserved = sum(min(m.product_uom_qty, m.quantity) for m in mo.move_raw_ids)
                mo.readiness_percentage = (total_reserved / total_demand) * 100
            else:
                mo.readiness_percentage = 100.0

    def _compute_shortage_count(self):
        for mo in self:
            mo.shortage_line_count = len(mo.move_raw_ids.filtered(lambda m: m.quantity < m.product_uom_qty))
