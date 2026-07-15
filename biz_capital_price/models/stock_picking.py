# -*- coding: utf-8 -*-


from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        return super(StockPicking, self.with_context(is_button_validate=True)).button_validate()

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        self.create_internal_transfer_layer()
        return res

    def create_internal_transfer_layer(self):
        for res in self:
            for line in res.move_line_ids_without_package:
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