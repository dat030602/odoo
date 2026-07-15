# -*- coding: utf-8 -*-

from odoo import fields, models, api

class StockMove(models.Model):
    _inherit = "stock.move"

    def _prepare_common_svl_vals(self):
        """When a `stock.valuation.layer` is created from a `stock.move`, we can prepare a dict of
        common vals.

        :returns: the common values when creating a `stock.valuation.layer` from a `stock.move`
        :rtype: dict
        """
        vals = super(StockMove, self)._prepare_common_svl_vals()
        move = self
        is_button_validate = self._context.get("is_button_validate")
        if move and move._is_out() and is_button_validate:
            new_unit_cost = move.move_orig_ids and move.move_orig_ids[0].price_unit
            if new_unit_cost:
                vals.update({
                    "unit_cost": new_unit_cost,
                    "is_custom_unit_cost": True
                })
        return vals

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    internal_transfer_price = fields.Float("Internal transfer price")
    internal_transfer_layer_ids = fields.One2many("stock.valuation.layer", 'interval_stock_move_line_id','Internal transfer layer')

    has_internal_transfer_layer = fields.Boolean('Đã có định giá nội bộ', 
        compute="_compute_has_internal_transfer_layer", store=False, search="search_has_internal_transfer_layer")

    def search_has_internal_transfer_layer(self, operator, value):
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            operator_new = 'inselect'
        else:
            operator_new = 'not inselect'

        query = """
          SELECT stock_move_id FROM stock_valuation_layer WHERE stock_move_id is not null
        """
        return [('move_id', operator_new, (query, ()))]

    @api.depends('internal_transfer_layer_ids')
    def _compute_has_internal_transfer_layer(self):
        for line in self:
            has_internal_transfer_layer = False
            if line.move_id.stock_valuation_layer_ids:
                has_internal_transfer_layer = True
            line.has_internal_transfer_layer = has_internal_transfer_layer
    
    @api.model_create_multi
    def create(self, vals_list):
        res = super(StockMoveLine, self).create(vals_list)
        res.create_internal_transfer_layer()
        return res

    def write(self, vals_list):
        res = super(StockMoveLine, self).write(vals_list)
        if 'qty_done' in vals_list:
            self.update_internal_transfer_layers()

        return res
    
    def update_internal_transfer_layers(self):
        for res in self:
            layers = self.env['stock.valuation.layer'].sudo().search([
                    ('interval_stock_move_line_id','=', res.id)
                ])

            for layer in layers:
                if layer.quantity < 0:
                    layer.quantity = - res.qty_done
                else:
                    layer.quantity = res.qty_done

    def create_internal_transfer_layer(self):
        for line in self.filtered(lambda x: x.state == 'done'):
            if line.internal_transfer_layer_ids:
                continue
            
            layers = line.move_id.stock_valuation_layer_ids.filtered(lambda x: x.is_create_from_average_period)
            if layers:
                continue

            if line.location_id.usage != 'internal' or line.location_dest_id.usage != 'internal':
                continue

            if not line.location_id.warehouse_id or line.location_id.warehouse_id == line.location_dest_id.warehouse_id:
                continue

            qty_done = line.product_uom_id._compute_quantity(line.qty_done, line.product_id.uom_id)
            svl_data = {
                'product_id': line.product_id.id,
                'stock_move_id': line.move_id.id,
                'quantity': qty_done,
                'unit_cost': 0,
                'value': 0,
                'company_id': self.env.company.id,
                'interval_stock_move_line_id': line.id,
            }
            svl1 = self.env['stock.valuation.layer'].create(svl_data)
            self.env.cr.execute("UPDATE stock_valuation_layer SET create_date=%s WHERE id=%s", (line.date, svl1.id))
            svl_data2 = {
                'product_id': line.product_id.id,
                'stock_move_id': line.move_id.id,
                'quantity': -qty_done,
                'unit_cost': 0,
                'value': 0,
                'interval_stock_move_line_id': line.id,
                'company_id': self.env.company.id,
            }
            svl2 = self.env['stock.valuation.layer'].create(svl_data2)
            self.env.cr.execute("UPDATE stock_valuation_layer SET create_date=%s WHERE id=%s", (line.date, svl2.id))
            
    @api.model
    def _create_correction_svl(self, move, diff):
        stock_valuation_layers = self.env['stock.valuation.layer']
        if move._is_in() and diff > 0 or move._is_out() and diff < 0:
            move.product_price_update_before_done(forced_qty=diff)
            stock_valuation_layers |= move._create_in_svl(forced_quantity=abs(diff))
            if move.product_id.cost_method in ('average', 'fifo'):
                move.product_id._run_fifo_vacuum(move.company_id)
        elif move._is_in() and diff < 0 or move._is_out() and diff > 0:
            stock_valuation_layers |= move._create_out_svl(forced_quantity=abs(diff))
        elif move._is_dropshipped() and diff > 0 or move._is_dropshipped_returned() and diff < 0:
            stock_valuation_layers |= move._create_dropshipped_svl(forced_quantity=abs(diff))
        elif move._is_dropshipped() and diff < 0 or move._is_dropshipped_returned() and diff > 0:
            stock_valuation_layers |= move._create_dropshipped_returned_svl(forced_quantity=abs(diff))

        if move.picking_id.state == 'done' and move.picking_id.date_done:
            for layer in stock_valuation_layers:
                self.env.cr.execute("UPDATE stock_valuation_layer SET create_date=%s WHERE id=%s", (move.picking_id.date_done, layer.id))
        stock_valuation_layers._validate_accounting_entries()