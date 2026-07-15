from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

class SummaryIEInventoryLine(models.Model):
	_name = 'summary.ie.inventory.line'
	_description = 'Summary of import and export inventory line'
	_order = 'stock_valuation_account_id, product_id, warehouse_id, qty_end desc'

	summary_id = fields.Many2one('summary.ie.inventory', ondelete='cascade')
	stock_valuation_account_id = fields.Many2one('account.account', 'Tài khoản kho')
	product_code = fields.Char('Mã sản phẩm', related='product_id.default_code')
	product_id = fields.Many2one('product.product', 'Sản phẩm')
	warehouse_id = fields.Many2one("stock.warehouse", 'Kho')
	uom_id = fields.Many2one('uom.uom', 'Đơn vị tính', related='product_id.uom_id')
	currency_id = fields.Many2one('res.currency', string='Tiền tệ', default=lambda self: self.env.company.currency_id)

	# Tồn đầu kỳ
	qty_begin = fields.Float('Số lượng tồn đầu', digits="Product Unit of Measure")
	value_begin = fields.Monetary('Giá trị tồn đầu')

	# Nhập
	# Nhập mua
	qty_import_purchase = fields.Float('Số lượng nhập mua', digits="Product Unit of Measure")
	value_import_purchase = fields.Monetary('Giá trị nhập mua')
	# Nhập sản xuất
	qty_import_production = fields.Float('Số lượng nhập sản xuất', digits="Product Unit of Measure")
	value_import_production = fields.Monetary('Giá trị nhập sản xuất')
	# Nhập hàng kiểm kê
	qty_import_inventory_adjustment = fields.Float('Số lượng nhập kiểm kê', digits="Product Unit of Measure")
	value_import_inventory_adjustment = fields.Monetary('Giá trị nhập kiểm kê')
	# Nhập nội bộ
	qty_import_internal = fields.Float('Số lượng nhập nội bộ', digits="Product Unit of Measure")
	value_import_internal = fields.Monetary('Giá trị nhập nội bộ')
	# Nhập khác
	qty_import_other = fields.Float('Số lượng nhập khác', digits="Product Unit of Measure")
	value_import_other = fields.Monetary('Giá trị nhập khác')
	# Tổng nhập
	qty_import_total = fields.Float('Tổng số lượng nhập', digits="Product Unit of Measure", compute='_compute_qty_import_total', store=True)
	value_import_total = fields.Monetary('Tổng giá trị nhập', compute='_compute_value_import_total', store=True)
	average_price = fields.Monetary('Giá bình quân', compute='_compute_average_price', store=True)
	allocated_cost = fields.Monetary('Giá trị phân bổ')

	@api.depends('qty_import_purchase', 'qty_import_production', 'qty_import_inventory_adjustment', 'qty_import_internal', 'qty_import_other')
	def _compute_qty_import_total(self):
		for line in self:
			line.qty_import_total = line.qty_import_purchase + line.qty_import_production + line.qty_import_inventory_adjustment + line.qty_import_internal + line.qty_import_other

	@api.depends('value_import_purchase', 'value_import_production', 'value_import_inventory_adjustment', 'value_import_internal', 'value_import_other')
	def _compute_value_import_total(self):
		for line in self:
			line.value_import_total = line.value_import_purchase + line.value_import_production + line.value_import_inventory_adjustment + line.value_import_internal + line.value_import_other

	@api.depends('qty_import_total', 'value_import_total')
	def _compute_average_price(self):
		for line in self:
			qty = line.qty_import_total + line.qty_begin
			value = line.value_import_total + line.value_begin
			line.average_price = value / (qty if qty else 1)

	# Xuất
	# Xuất bán hàng
	qty_export_sale = fields.Float('Số lượng xuất bán', digits="Product Unit of Measure")
	value_export_sale = fields.Float('Doanh thu xuất bán')
	value_export_sale_cost = fields.Float('Giá vốn xuất bán')
	value_export_sale_profit = fields.Float('Lãi gộp xuất bán', compute='_compute_value_export_sale_profit', store=True)

	@api.depends('value_export_sale', 'value_export_sale_cost')
	def _compute_value_export_sale_profit(self):
		for line in self:
			line.value_export_sale_profit = line.value_export_sale - line.value_export_sale_cost

	# Xuất sản xuất
	qty_export_production = fields.Float('Số lượng xuất sản xuất', digits="Product Unit of Measure")
	value_export_production = fields.Float('Giá trị xuất sản xuất')
	# Xuất hàng kiểm kê
	qty_export_inventory_adjustment = fields.Float('Số lượng xuất kiểm kê', digits="Product Unit of Measure")
	value_export_inventory_adjustment = fields.Float('Giá trị xuất kiểm kê')
	# Xuất nội bộ
	qty_export_internal = fields.Float('Số lượng xuất nội bộ', digits="Product Unit of Measure")
	value_export_internal = fields.Float('Giá trị xuất nội bộ')
	# Xuất khác
	qty_export_other = fields.Float('Số lượng xuất khác', digits="Product Unit of Measure")
	value_export_other = fields.Float('Giá trị xuất khác')
	# Tổng xuất
	qty_export_total = fields.Float('Tổng số lượng xuất', digits="Product Unit of Measure", compute='_compute_qty_export_total', store=True)
	value_export_total = fields.Float('Tổng giá trị xuất', compute='_compute_value_export_total', store=True)

	@api.depends('qty_export_sale', 'qty_export_production', 'qty_export_inventory_adjustment', 'qty_export_internal', 'qty_export_other')
	def _compute_qty_export_total(self):
		for line in self:
			line.qty_export_total = line.qty_export_sale + line.qty_export_production + line.qty_export_inventory_adjustment + line.qty_export_internal + line.qty_export_other

	@api.depends('value_export_sale_cost', 'value_export_production', 'value_export_inventory_adjustment', 'value_export_internal', 'value_export_other')
	def _compute_value_export_total(self):
		for line in self:
			line.value_export_total = line.value_export_sale_cost + line.value_export_production + line.value_export_inventory_adjustment + line.value_export_internal + line.value_export_other

	# Tồn cuối kỳ
	qty_end = fields.Float('Số lượng tồn cuối', digits="Product Unit of Measure", compute='_compute_qty_end', store=True)
	value_end = fields.Float('Giá trị tồn cuối', compute='_compute_value_end', store=True)

	@api.depends('qty_begin', 'qty_import_total', 'qty_export_total')
	def _compute_qty_end(self):
		for line in self:
			line.qty_end = line.qty_begin + line.qty_import_total - line.qty_export_total

	@api.depends('value_begin', 'value_import_total', 'value_export_total', 'allocated_cost')
	def _compute_value_end(self):
		for line in self:
			line.value_end = line.value_begin + line.value_import_total + line.allocated_cost - line.value_export_total

	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

	def _prepare_create_value(self, summary_id, warehouse_id, product_id, **kwargs):
		result = self._generate_json(**kwargs)
		result.update({
			'summary_id': summary_id,
			'product_id': product_id.id,
			'warehouse_id': warehouse_id.id if warehouse_id else False,
			'stock_valuation_account_id': product_id.categ_id.property_stock_valuation_account_id.id,
		})
		return result

	def _generate_json(self, **kwargs):
		# Danh sách các trường cần kiểm tra
		self = self.sudo()
		fields_list = [
			'qty_begin',
			'value_begin',
			'qty_import_purchase',
			'value_import_purchase',
			'qty_import_production',
			'value_import_production',
			'qty_import_inventory_adjustment',
			'value_import_inventory_adjustment',
			'qty_import_internal',
			'value_import_internal',
			'qty_import_other',
			'value_import_other',
			'qty_export_sale',
			'value_export_sale',
			'value_export_sale_cost',
			'qty_export_production',
			'value_export_production',
			'qty_export_inventory_adjustment',
			'value_export_inventory_adjustment',
			'qty_export_internal',
			'value_export_internal',
			'qty_export_other',
			'value_export_other',
			'allocated_cost',
		]
		result = {}
		for field in fields_list:
			result[field] = kwargs.get(field, 0)
		return result
