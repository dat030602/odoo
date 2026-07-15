#-*- coding: utf-8 -*-

from odoo import fields, models
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, mute_logger

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	def action_update_inventory_quant(self):
		for product in self.product_variant_ids:
			product.action_update_inventory_quant()

	def cron_update_inventory_all_product(self):
		products = self.search([])
		for product in products:
			product.action_update_inventory_quant()
			
class ProductProduct(models.Model):
	_inherit = 'product.product'

	def action_update_inventory_quant(self):
		for res in self.filtered(lambda x: x.type == 'product'):
			if res.tracking:
				res.action_update_inventory_quant_lot()

	def action_update_inventory_quant_lot(self):
		res = self
		domain = [
			('product_id', '=', res.id),
			('state','in', ['done','partially_available','assigned'])
		]
		move_ids = self.env['stock.move.line'].sudo().search(domain)

		group_lot = {}

		group_tu = {}
		group_toi = {}

		product_uom = res.uom_id
		
		for move in move_ids:
			lot = group_lot.setdefault(move.lot_id, {
				'group_tu': {},
				'group_toi': {},
				'locations': self.env['stock.location']
			})

			move_uom = move.product_uom_id
			if move.location_id.usage == 'internal':
				lot['locations'] |= move.location_id
				tu = lot['group_tu'].setdefault(move.location_id, {
						'qty_done': 0,
						'qty_assign': 0
					})
				if move.state == 'done':
					tu['qty_done'] += move_uom._compute_quantity(move.qty_done, product_uom, rounding_method='HALF-UP',raise_if_failure=False)
				else:
					tu['qty_assign'] += move_uom._compute_quantity(move.reserved_uom_qty, product_uom, rounding_method='HALF-UP', raise_if_failure=False)

			if move.location_dest_id.usage == 'internal':
				lot['locations'] |= move.location_dest_id
				toi = lot['group_toi'].setdefault(move.location_dest_id, {
						'qty_done': 0,
						'qty_assign': 0
					})
				if move.state == 'done':
					toi['qty_done'] += move_uom._compute_quantity(move.qty_done, product_uom, rounding_method='HALF-UP', raise_if_failure=False)
				else:
					toi['qty_assign'] += move_uom._compute_quantity(move.reserved_uom_qty, product_uom, rounding_method='HALF-UP', raise_if_failure=False)

		for lot, data in group_lot.items():
			group_tu = data['group_tu']
			group_toi = data['group_toi']
			locations = data['locations']
			
			for loc in locations:
				quant_tu = group_tu.get(loc, {}) or {}
				quant_toi = group_toi.get(loc, {}) or {}

				qty_done = quant_tu.get('qty_done', 0)
				qty_assgin = quant_tu.get('qty_assign', 0)
				# Calculate decimal places from UOM rounding (e.g., 0.01 -> 2, 0.001 -> 3)
				decimal_places = len(str(product_uom.rounding).split('.')[-1].rstrip('0')) if product_uom.rounding < 1 else 0
				qty_assgin = round(qty_assgin, decimal_places)

				available_qty = quant_toi.get('qty_done', 0) - qty_done
				available_qty = round(available_qty, decimal_places)
				quant_id = self.env['stock.quant'].search([
					("product_id",'=', res.id),
					('location_id','=', loc.id),
					("lot_id",'=', lot.id)
				])

				in_date = datetime.strftime(datetime.now(), DEFAULT_SERVER_DATETIME_FORMAT)

				if not quant_id:
					self.env.cr.execute("""
						insert into stock_quant (product_id, lot_id, location_id, quantity, reserved_quantity, in_date) 
						values (%s,%s,%s,%s,%s,'%s')
						""" % (res.id, lot and lot.id or 'null', loc.id, available_qty, qty_assgin, in_date))

				elif len(quant_id) == 1:
					if quant_id.quantity != available_qty:
						self.env.cr.execute("""
							update stock_quant set quantity = %s where id = %s
						""" % (available_qty, quant_id.id))

					if quant_id.reserved_quantity !=  qty_assgin:
						self.env.cr.execute("""
							update stock_quant set reserved_quantity = %s where id = %s
						""" % (qty_assgin, quant_id.id))
