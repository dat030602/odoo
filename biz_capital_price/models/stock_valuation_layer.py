# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import timedelta

class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    average_period_id = fields.Many2one("average.capital.price.end.period", index=True)
    initial_value = fields.Monetary("Initial value", compute='compute_initial_value', store=True)
    interval_move_id = fields.Many2one("account.move", 'Internal transfer move')
    interval_stock_move_line_id = fields.Many2one("stock.move.line", 'Interval stock move line')
    is_create_from_average_period = fields.Boolean(copy=False)

    @api.depends("value")
    def compute_initial_value(self):
        for res in self:
            if not res.initial_value and res.value:
                res.initial_value = res.value

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "stock_move_id" in vals and "is_custom_unit_cost" in vals:
                company_id = self.env.context.get('force_company', self.env.company.id)
                company = self.env['res.company'].browse(company_id)
                currency = company.currency_id
                move = self.env['stock.move'].browse(vals["stock_move_id"])
                if move._is_out() and "quantity" in vals and "unit_cost" in vals and "value" in vals and currency:
                    new_value = currency.round(vals["quantity"] * vals["unit_cost"]) if currency.round(vals["quantity"] * vals["unit_cost"]) != vals["value"] else vals["value"]
                    vals.update({"value": new_value})
                del vals["is_custom_unit_cost"]
        return super(StockValuationLayer, self).create(vals_list)

    def layer_update_date_account_move(self):
        """
        Update the date of the account move related to the stock valuation layer
        """
        for layer in self:
            date = (layer.create_date + timedelta(hours=7)).date()
            if layer.account_move_id and layer.account_move_id.date != date:
                layer.account_move_id.date = date


    @api.depends('stock_move_id','stock_move_id.move_line_ids')
    def _compute_location(self):
        internal_layers = self.filtered(lambda x: x.interval_stock_move_line_id)
        for res in internal_layers:
            res.location_id = res.interval_stock_move_line_id.location_id
            res.location_dest_id = res.interval_stock_move_line_id.location_dest_id

        return super(StockValuationLayer, self - internal_layers)._compute_location()
        