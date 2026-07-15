# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AllocationDetailsByAccount(models.Model):
    _name = "allocation.details.by.account"
    _description = "Allocation Details By Account"
    
    period_line_id = fields.Many2one('average.capital.price.end.period.line', string='Period', ondelete='cascade')
    end_period_cost_allocation_id = fields.Many2one('end.period.cost.allocation', string='End Period Cost Allocation', ondelete='cascade')
    account_ids = fields.Many2many('account.account', string='Account')
    allocated_value_for_product = fields.Float(string='Allocated Value for Product', compute="compute_allocated_value_for_product", store=True)
    
    @api.depends('end_period_cost_allocation_id', 'period_line_id', 'period_line_id.actual_value_import', 'period_line_id.total_value_import')
    def compute_allocated_value_for_product(self):
        for rec in self:
            if rec.end_period_cost_allocation_id.value > 0:
                total = (rec.period_line_id.actual_value_import - rec.period_line_id.total_value_import) / rec.end_period_cost_allocation_id.mass_period_id.total_allocation_value * rec.end_period_cost_allocation_id.value
                rec.allocated_value_for_product = total if total > 0 else 0.0
            else:
                rec.allocated_value_for_product = 0.0
    