# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare, float_round

class MrpProductionSplit(models.TransientModel):
    _inherit = 'mrp.production.split'

    counter = fields.Integer(
        "Split #", default=1, compute="_compute_counter",
        store=True, readonly=False)

    @api.depends('production_detailed_vals_ids')
    def _compute_valid_details(self):
        self.valid_details = False
        for wizard in self:
            if wizard.production_detailed_vals_ids:
                wizard.valid_details = True

    def action_split(self):
        for wizard in self:
            commands = []
            qty = wizard.product_qty - sum(wizard.production_detailed_vals_ids.mapped('quantity'))
            if float_compare(qty, 0, precision_rounding=wizard.product_uom_id.rounding) <= 0:
                continue
            commands.append(Command.create({
                'quantity': qty,
                'user_id': wizard.production_id.user_id.id,
                'date': wizard.production_id.date_planned_start,
            }))
            wizard.production_detailed_vals_ids = commands
        self.env.cr.commit()
        res = super(MrpProductionSplit, self).action_split()
        return res