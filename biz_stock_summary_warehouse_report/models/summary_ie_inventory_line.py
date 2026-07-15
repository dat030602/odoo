from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, time, timedelta
import logging
	
_logger = logging.getLogger(__name__)

class SummaryIEInventoryLine(models.Model):
	_inherit = 'summary.ie.inventory.line'

	warehouse_id = fields.Many2one("stock.warehouse", 'Warehouse')

	is_show_moves = fields.Boolean('Is show moves', compute='_compute_is_show_moves', store=True)

	@api.depends('summary_id')
	def _compute_is_show_moves(self):
		for record in self:
			record.is_show_moves = record.qty_begin > 0 or record.qty_import_total > 0 or record.qty_export_total > 0

	@api.constrains('warehouse_id', 'company_id')
	def _check_company_summary(self):
		for record in self:
			if record.warehouse_id and record.warehouse_id.company_id != record.company_id:
				raise ValidationError(_('Warehouse must belong to the same company as the record.'))

	def action_view_moves(self):
		"""Action để xem chi tiết các moves"""
		context = {
			'search_default_done': 1,
			'search_default_product_id': self.product_id.id,
		}
		if self.warehouse_id:
			context['search_default_warehouse_id'] = self.warehouse_id.id
		action = self.env.ref('stock.stock_move_action').sudo().read()[0]
		action['domain'] = [
			('date', '>=', datetime.combine(self.summary_id.from_date, time.min) - timedelta(hours=7)),
			('date', '<=', datetime.combine(self.summary_id.to_date, time.max) - timedelta(hours=7)),
			'|',
			('location_id.warehouse_id', '=', self.warehouse_id.id),
			('location_dest_id.warehouse_id', '=', self.warehouse_id.id),
		]
		action['context'] = context
		return action

	def _convert_uom_factor(self, from_uom, to_uom, quant):
		"""Convert UOM factor for quantity calculations"""
		from_factor = (1 / from_uom.factor) if from_uom.factor > 1 else 1
		to_factor = ((1 / to_uom.factor) if to_uom.factor > 1 else 1) / from_factor
		return quant * to_factor

	def get_qty_begin_value_begin(self, summary_id, product_id, warehouse):
		if summary_id.separate_warehouse_lines:
			last_line = summary_id.previous_period_id.line_ids.filtered(lambda x: x.product_id == product_id and x.warehouse_id == warehouse)
		else:
			last_line = summary_id.previous_period_id.line_ids.filtered(lambda x: x.product_id == product_id)
		return sum(last_line.mapped('qty_end')) or 0, sum(last_line.mapped('value_end')) or 0

	def _create_line(self, stock_moves, summary_id, warehouse_id):
		groups = {}
		remaining_moves = stock_moves
		allocated_cost = {}

		# Thêm dòng còn tồn ở kỳ trước
		if summary_id.separate_warehouse_lines:
			pre_product_ids = summary_id.previous_period_id.line_ids.filtered(lambda x: x.warehouse_id == warehouse_id).mapped('product_id')
		else:
			pre_product_ids = summary_id.previous_period_id.line_ids.mapped('product_id')
		for product_id in pre_product_ids:
			val = groups.setdefault(product_id, self._generate_json())
			qty_begin, value_begin = self.get_qty_begin_value_begin(summary_id, product_id, warehouse_id)
			if qty_begin != 0 or value_begin != 0:
				val.update({
					'qty_begin': qty_begin,
					'value_begin': value_begin,
				})
		
		# Chi phí phân bổ: chỉ tính cho các sản phẩm có nhập khẩu (mua hoặc sản xuất) trong kỳ, không tính cho các sản phẩm chỉ có tồn đầu kỳ hoặc chỉ xuất khẩu trong kỳ
		if stock_moves:
			lines = self.env['average.capital.price.end.period.line'].search([
				('period_id.from_date', '>=', summary_id.from_date),
				('period_id.to_date', '<=', summary_id.to_date),
				('product_id', 'in', stock_moves.mapped('product_id').ids),
				('period_id.mass_period_id', '!=', False),
			])
			product_ids = lines.mapped('product_id')
			for product_id in product_ids:
				line = lines.filtered(lambda l: l.product_id == product_id)
				allocated_cost[product_id] = sum(line.mapped('allocation_details_by_account_ids.allocated_value_for_product'))
		
		# Internal moves: same warehouse, both internal
		moves = remaining_moves.filtered(
			lambda m: m.location_id.warehouse_id == warehouse_id
			and m.location_id.usage == 'internal'
			and m.location_dest_id.usage == 'internal'
		)
		for stock_move in moves:
			val = groups.setdefault(stock_move.product_id, self._generate_json())
			values = [v.value for v in stock_move.stock_valuation_layer_ids if v.value > 0]
			value = sum(values) if values else 0
			quantity = self._convert_uom_factor(stock_move.product_id.uom_id, stock_move.product_uom, stock_move.quantity_done)
			val.update({
				'qty_export_internal': val.get('qty_export_internal', 0) + quantity,
				'value_export_internal': val.get('value_export_internal', 0) + abs(value),
			})
		remaining_moves = remaining_moves - moves

		# Internal moves: same warehouse, both internal (reverse direction)
		moves = remaining_moves.filtered(
			lambda m: warehouse_id == m.location_dest_id.warehouse_id
			and m.location_id.usage == 'internal'
			and m.location_dest_id.usage == 'internal'
		)
		for stock_move in moves:
			val = groups.setdefault(stock_move.product_id, self._generate_json())
			values = [v.value for v in stock_move.stock_valuation_layer_ids if v.value > 0]
			value = sum(values) if values else 0
			quantity = self._convert_uom_factor(stock_move.product_id.uom_id, stock_move.product_uom, stock_move.quantity_done)
			val.update({
				'qty_import_internal': val.get('qty_import_internal', 0) + quantity,
				'value_import_internal': val.get('value_import_internal', 0) + abs(value),
			})
		remaining_moves = remaining_moves - moves

		# Import form supplier: src warehouse == warehouse_id, src usage == 'supplier'
		moves = remaining_moves.filtered(
			lambda m: m.location_dest_id.warehouse_id == warehouse_id
			and m.location_id.usage == 'supplier'
		)
		for stock_move in moves:
			val = groups.setdefault(stock_move.product_id, self._generate_json())
			values = stock_move.stock_valuation_layer_ids.mapped('value')
			value = sum(stock_move.stock_valuation_layer_ids.mapped('value')) if values else 0
			quantity = self._convert_uom_factor(stock_move.product_id.uom_id, stock_move.product_uom, stock_move.quantity_done)
			val.update({
				'qty_import_purchase': val.get('qty_import_purchase', 0) + quantity,
				'value_import_purchase': val.get('value_import_purchase', 0) + abs(value),
			})
		remaining_moves = remaining_moves - moves
		
		# Import from production: src warehouse == warehouse_id, dest usage == 'production'
		moves = remaining_moves.filtered(
			lambda m: m.location_id.usage == 'production'
			and m.location_dest_id.warehouse_id == warehouse_id
		)
		for stock_move in moves:
			val = groups.setdefault(stock_move.product_id, self._generate_json())
			value = stock_move.stock_valuation_layer_ids.mapped('value')
			value = sum(value) if value else 0
			quantity = self._convert_uom_factor(stock_move.product_id.uom_id, stock_move.product_uom, stock_move.quantity_done)
			val.update({
				'qty_import_production': val.get('qty_import_production', 0) + quantity,
				'value_import_production': val.get('value_import_production', 0) + abs(value),
			})
		remaining_moves = remaining_moves - moves

		# Export to production: dest warehouse == warehouse_id, src usage == 'production'
		moves = remaining_moves.filtered(
			lambda m: m.location_dest_id.usage == 'production'
			and m.location_id.warehouse_id == warehouse_id
		)
		for stock_move in moves:
			val = groups.setdefault(stock_move.product_id, self._generate_json())
			values = stock_move.stock_valuation_layer_ids.mapped('value')
			value = sum(values) if values else 0
			quantity = self._convert_uom_factor(stock_move.product_id.uom_id, stock_move.product_uom, stock_move.quantity_done)
			val.update({
				'qty_export_production': val.get('qty_export_production', 0) + quantity,
				'value_export_production': val.get('value_export_production', 0) + abs(value),
			})
		remaining_moves = remaining_moves - moves
		
		# Import from inventory: dest warehouse == warehouse_id, src usage == 'inventory'
		moves = remaining_moves.filtered(
			lambda m: m.location_id.usage == 'inventory'
			and m.location_dest_id.warehouse_id == warehouse_id
		)
		for stock_move in moves:
			val = groups.setdefault(stock_move.product_id, self._generate_json())
			values = stock_move.stock_valuation_layer_ids.mapped('value')
			value = sum(values) if values else 0
			quantity = self._convert_uom_factor(stock_move.product_id.uom_id, stock_move.product_uom, stock_move.quantity_done)
			val.update({
				'qty_import_inventory_adjustment': val.get('qty_import_inventory_adjustment', 0) + quantity,
				'value_import_inventory_adjustment': val.get('value_import_inventory_adjustment', 0) + abs(value),
			})
		remaining_moves = remaining_moves - moves

		# Export to inventory: src warehouse == warehouse_id, dest usage == 'inventory'
		moves = remaining_moves.filtered(
			lambda m: m.location_id.warehouse_id == warehouse_id
			and m.location_dest_id.usage == 'inventory'
		)
		for stock_move in moves:
			val = groups.setdefault(stock_move.product_id, self._generate_json())
			values = stock_move.stock_valuation_layer_ids.mapped('value')
			value = sum(values) if values else 0
			quantity = self._convert_uom_factor(stock_move.product_id.uom_id, stock_move.product_uom, stock_move.quantity_done)
			val.update({
				'qty_export_inventory_adjustment': val.get('qty_export_inventory_adjustment', 0) + quantity,
				'value_export_inventory_adjustment': val.get('value_export_inventory_adjustment', 0) + abs(value),
			})
		remaining_moves = remaining_moves - moves
		
		# Export to customer: src warehouse == warehouse_id, src usage == 'customer'
		moves = remaining_moves.filtered(
			lambda m: m.location_id.warehouse_id == warehouse_id
			and m.location_dest_id.usage == 'customer' and 'customer' in m.location_dest_id.name.lower()
		)
		for stock_move in moves:
			val = groups.setdefault(stock_move.product_id, self._generate_json())
			values = stock_move.stock_valuation_layer_ids.mapped('value')
			unit_cost = stock_move.sale_line_id.price_unit if stock_move.sale_line_id else 0
			quantity = self._convert_uom_factor(stock_move.product_id.uom_id, stock_move.product_uom, stock_move.quantity_done)
			value = unit_cost * quantity
			val.update({
				'qty_export_sale': val.get('qty_export_sale', 0) + quantity,
				'value_export_sale': val.get('value_export_sale', 0) + abs(value),
				'value_export_sale_cost': val.get('value_export_sale_cost', 0) + abs(sum(values)) if values else 0,
			})
		remaining_moves = remaining_moves - moves
		
		# Other cases: remaining moves
		for stock_move in remaining_moves:
			val = groups.setdefault(stock_move.product_id, self._generate_json())
			values = stock_move.stock_valuation_layer_ids.mapped('value')
			value = sum(values) if values else 0
			qty_field = 'qty_import_other'
			value_field = 'value_import_other'
			if stock_move.location_id.warehouse_id == warehouse_id:
				qty_field = 'qty_export_other'
				value_field = 'value_export_other'
			quantity = self._convert_uom_factor(stock_move.product_id.uom_id, stock_move.product_uom, stock_move.quantity_done)
			val.update({
				qty_field: val.get(qty_field, 0) + quantity,
				value_field: val.get(value_field, 0) + abs(value),
			})

		vals = []
		for product_id, val in groups.items():
			if val.get('qty_import_purchase', 0) > 0 or val.get('qty_import_production', 0) > 0:
				val.update({
					'allocated_cost': allocated_cost.get(product_id, 0),
				})
			vals.append(self._prepare_create_value(summary_id.id, warehouse_id, product_id, **val))

		# Thêm dòng không phát sinh
		if summary_id.currently_there_are_no_products_available:
			domain = [('detailed_type', '=', 'product')]
			if summary_id.product_category_ids:
				domain += [('categ_id', 'in', summary_id.product_category_ids.ids)]
			product_ids = self.env['product.product'].search(domain) - (stock_moves.mapped('product_id') + pre_product_ids)
			for product_id in product_ids:
				vals.append(self._prepare_create_value(summary_id.id, warehouse_id, product_id))
		return vals

	def _get_data_export(self):
		self.ensure_one()
		return {
			'stock_valuation_account_id': self.stock_valuation_account_id.display_name if self.stock_valuation_account_id else '',
			'product_code': self.product_code,
			'product_id': self.product_id.name if self.product_id else '',
			'warehouse_id': self.warehouse_id.code if self.warehouse_id else '',
			'uom_id': self.uom_id.name if self.uom_id else '',
			'currency_id': self.currency_id.name if self.currency_id else '',
			'qty_begin': self.qty_begin,
			'value_begin': self.value_begin,
			'qty_import_purchase': self.qty_import_purchase,
			'value_import_purchase': self.value_import_purchase,
			'qty_import_production': self.qty_import_production,
			'value_import_production': self.value_import_production,
			'qty_import_inventory_adjustment': self.qty_import_inventory_adjustment,
			'value_import_inventory_adjustment': self.value_import_inventory_adjustment,
			'qty_import_internal': self.qty_import_internal,
			'value_import_internal': self.value_import_internal,
			'qty_import_other': self.qty_import_other,
			'value_import_other': self.value_import_other,
			'qty_import_total': self.qty_import_total,
			'value_import_total': self.value_import_total,
			'average_price': self.average_price,
			'qty_export_sale': self.qty_export_sale,
			'value_export_sale': self.value_export_sale,
			'value_export_sale_cost': self.value_export_sale_cost,
			'value_export_sale_profit': self.value_export_sale_profit,
			'qty_export_production': self.qty_export_production,
			'value_export_production': self.value_export_production,
			'qty_export_inventory_adjustment': self.qty_export_inventory_adjustment,
			'value_export_inventory_adjustment': self.value_export_inventory_adjustment,
			'qty_export_internal': self.qty_export_internal,
			'value_export_internal': self.value_export_internal,
			'qty_export_other': self.qty_export_other,
			'value_export_other': self.value_export_other,
			'qty_export_total': self.qty_export_total,
			'value_export_total': self.value_export_total,
			'qty_end': self.qty_end,
			'value_end': self.value_end,
		}
