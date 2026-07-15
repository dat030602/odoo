# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.tools import float_compare, float_is_zero


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    location_id = fields.Many2one('stock.location', compute="_compute_location", store=True)
    location_dest_id = fields.Many2one('stock.location', compute="_compute_location", store=True)

    def update_location(self):
        search_self = self.search([],limit=20000)
        for se in search_self:
            try:
                se._compute_location()
            except:
                pass

    @api.depends('stock_move_id','stock_move_id.move_line_ids')
    def _compute_location(self):
        for res in self:
            res.location_id = False
            res.location_dest_id = False
            for line in res.stock_move_id.move_line_ids:
                res.location_id = line.location_id
                res.location_dest_id = line.location_dest_id
                break


