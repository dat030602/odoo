# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from datetime import timedelta
from odoo.tools import float_compare, float_is_zero

class StockMove(models.Model):
	_inherit = 'stock.move'

	def write(self, val):
		if 'date' in val:
			for res in self:
				unbuild_id = res.unbuild_id
				if val.get("unbuild_id", False):
					unbuild_id = self.env['mrp.unbuild'].browse(val['unbuild_id'])
				
				if unbuild_id and unbuild_id.actual_date:
					if 'date' in val:
						val['date'] = unbuild_id.actual_date

		res = super(StockMove, self).write(val)
		return res

class MrpUnbuild(models.Model):
	_inherit = 'mrp.unbuild'

	actual_date = fields.Datetime('Actual date')

	def _generate_move_from_existing_move(self, move, factor, location_id, location_dest_id):
		return self.env['stock.move'].create({
			'name': self.name,
			'date': self.actual_date or self.create_date,
			'product_id': move.product_id.id,
			'product_uom_qty': move.quantity_done * factor,
			'product_uom': move.product_uom.id,
			'procure_method': 'make_to_stock',
			'location_dest_id': location_dest_id.id,
			'location_id': location_id.id,
			'warehouse_id': location_dest_id.warehouse_id.id,
			'unbuild_id': self.id,
			'company_id': move.company_id.id,
			'origin_returned_move_id': move.id,
		})

	def _generate_move_from_bom_line(self, product, product_uom, quantity, bom_line_id=False, byproduct_id=False):
		product_prod_location = product.with_company(self.company_id).property_stock_production
		location_id = bom_line_id and product_prod_location or self.location_id
		location_dest_id = bom_line_id and self.location_dest_id or product_prod_location
		warehouse = location_dest_id.warehouse_id
		return self.env['stock.move'].create({
			'name': self.name,
			'date': self.actual_date or self.create_date,
			'bom_line_id': bom_line_id,
			'byproduct_id': byproduct_id,
			'product_id': product.id,
			'product_uom_qty': quantity,
			'product_uom': product_uom.id,
			'procure_method': 'make_to_stock',
			'location_dest_id': location_dest_id.id,
			'location_id': location_id.id,
			'warehouse_id': warehouse.id,
			'unbuild_id': self.id,
			'company_id': self.company_id.id,
		})

	def update_old_produce_line_date(self):
		for res in self.filtered(lambda x: x.actual_date):
			for line in res.produce_line_ids:
				line.write({
					'date': res.actual_date
				})
				line.move_line_ids.write({
					'date': res.actual_date
				})
				line.account_move_ids.write({
					'date': (res.actual_date + timedelta(hours=7)).date()
				})
				for layer in line.stock_valuation_layer_ids:
					self.env.cr.execute("UPDATE stock_valuation_layer SET create_date=%s WHERE id=%s", (res.actual_date, layer.id))