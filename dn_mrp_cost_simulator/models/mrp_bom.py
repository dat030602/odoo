from odoo import fields, models, _


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    simulation_ids = fields.One2many(
        'mrp.bom.simulation',
        'bom_id',
        string='Cost Simulations'
    )
    simulation_count = fields.Integer(
        string='Simulations Count',
        compute='_compute_simulation_count'
    )

    def _compute_simulation_count(self):
        sim_data = self.env['mrp.bom.simulation']._read_group(
            domain=[('bom_id', 'in', self.ids)],
            groupby=['bom_id'],
            aggregates=['__count']
        )
        mapped_count = {bom.id: count for bom, count in sim_data}
        for bom in self:
            bom.simulation_count = mapped_count.get(bom.id, 0)

    def action_view_simulations(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('dn_mrp_cost_simulator.action_mrp_bom_simulation')
        action['domain'] = [('bom_id', '=', self.id)]
        action['context'] = {'default_bom_id': self.id}
        return action

    def action_create_simulation(self):
        self.ensure_one()
        sim = self.env['mrp.bom.simulation'].create({
            'bom_id': self.id,
            'description': _('Simulation for %s') % self.display_name,
            'product_qty': self.product_qty or 1.0,
        })
        sim.action_load_from_bom()
        return {
            'type': 'ir.actions.act_window',
            'name': _('BOM Cost Simulation'),
            'res_model': 'mrp.bom.simulation',
            'res_id': sim.id,
            'view_mode': 'form',
            'target': 'current',
        }
