from odoo import models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def action_view_cost_variance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cost Variance Analysis - %s') % self.name,
            'res_model': 'mrp.cost.variance.matrix',
            'view_mode': 'list,pivot',
            'domain': [('production_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_consumption_variance(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Consumption Variance - %s') % self.name,
            'res_model': 'mrp.cost.consumption.variance',
            'view_mode': 'list,pivot',
            'domain': [('production_id', '=', self.id)],
            'target': 'current',
        }
