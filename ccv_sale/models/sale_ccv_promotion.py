# -*- coding: utf-8 -*-

from odoo import models, fields, api
import ast
from odoo.exceptions import ValidationError

class SaleCcvPromotion(models.Model):
	_name = 'sale.ccv.promotion'
	_description = 'Khuyến mãi bán hàng CCV'
	_order = 'date_from desc'
	_inherit = ['mail.thread', 'mail.activity.mixin']

	name = fields.Char(string="Tên", tracking=True)
	date_from = fields.Date(string="Từ ngày", required=True, tracking=True)
	date_to = fields.Date(string="Đến ngày", required=True, tracking=True)
	team_id = fields.Many2one('crm.team', string="Nhóm kinh doanh", tracking=True)
	partner_domain = fields.Char(string="Điều kiện khách hàng", default="[]", required=True, tracking=True)
	product_domain = fields.Char(string="Điều kiện sản phẩm", default="[]", required=True, tracking=True)

	type = fields.Selection([('percentage', 'Phần trăm'), ('fixed', 'Cố định'), ('gift', 'Quà tặng')], string="Loại khuyến mãi", required=True, tracking=True)
	amount = fields.Monetary(string="Giá trị", required=True, tracking=True)
	amount_percentage = fields.Float(string="Phần trăm giá trị", required=True, tracking=True)
	currency_id = fields.Many2one('res.currency', string="Loại tiền tệ", required=True, default=lambda self: self.env.company.currency_id, tracking=True)
	gift_product_id = fields.Many2one('product.product', string="Sản phẩm quà tặng", domain=[('sale_ok', '=', True)], tracking=True)
	gift_quantity = fields.Float(string="Số lượng quà tặng", default=1, tracking=True, digits="Product Unit of Measure")
	min_amount_total = fields.Monetary(string="Tổng giá trị tối thiểu", default=0, tracking=True)
	min_quantity_total = fields.Float(string="Tổng số lượng tối thiểu", default=0, tracking=True, digits="Product Unit of Measure")
	is_default = fields.Boolean(string="Mặc định", default=False, tracking=True)
	
	active = fields.Boolean(string="Hoạt động", default=True, tracking=True)

	@api.constrains('date_from', 'date_to')
	def _check_date(self):
		for rec in self:
			if rec.date_from > rec.date_to:
				raise ValidationError("Ngày bắt đầu phải trước ngày kết thúc")

	@api.constrains('type', 'gift_product_id')
	def _check_gift_promotion(self):
		for rec in self:
			if rec.type == 'gift' and not rec.gift_product_id:
				raise ValidationError("Loại khuyến mãi quà tặng bắt buộc phải chọn sản phẩm quà tặng")

	def name_get(self):
		result = []
		for rec in self:
			if (rec.type == 'fixed' and rec.amount == 0) or (rec.type == 'percentage' and rec.amount_percentage == 0):
				result.append((rec.id, rec.name))
			else:
				name = "[%s - %s]%s%s" % (rec.date_from.strftime("%d/%m/%Y"), rec.date_to.strftime("%d/%m/%Y"), (' - %s' % rec.name if rec.name else ""), (' - %s' % rec.team_id.report_name if rec.team_id else ""))
				result.append((rec.id, name))
		return result

	def _get_partner_by_domain(self):
		try:
			if not self.partner_domain:
				return self.env['res.partner']
			partner_domain = ast.literal_eval(self.partner_domain)
			return self.env['res.partner'].search(partner_domain)
		except Exception:
			return self.env['res.partner']

	def _get_product_by_domain(self):
		try:
			if not self.product_domain:
				return self.env['product.product'] 
			product_domain = ast.literal_eval(self.product_domain)
			return self.env['product.product'].search(product_domain)
		except Exception:
			return self.env['product.product']

	def _check_promotion_applicable(self, sale_line_id):
		"""
		Kiểm tra promotion có thể áp dụng cho sale_line_id hay không.
		Dùng chung cho tất cả các loại promotion.
		"""
		self.ensure_one()
		order_date = sale_line_id.order_id.date_order.date() if sale_line_id.order_id.date_order else fields.Date.today()
		if self.date_from and order_date < self.date_from:
			return False
		if self.date_to and order_date > self.date_to:
			return False
		partner_domain = self.partner_domain if self.partner_domain else False
		if partner_domain and sale_line_id.order_id.partner_id not in self._get_partner_by_domain():
			return False
		product_domain = self.product_domain if self.product_domain else False
		if product_domain and sale_line_id.product_id not in self._get_product_by_domain():
			return False
		
		# Kiểm tra điều kiện tổng giá trị và số lượng cho tất cả các loại promotion
		return self._check_order_total_conditions(sale_line_id.order_id.id)

	def _get_promotion_amount(self, sale_line_id):
		"""
		Trả về số tiền khuyến mãi được áp dụng cho sale_line_id.
		Nếu không đủ điều kiện thì trả về 0.
		"""
		self.ensure_one()
		
		# Sử dụng hàm check chung
		if not self._check_promotion_applicable(sale_line_id):
			return 0
		
		if self.type == 'gift':
			if not self.gift_product_id:
				return 0
			return self.amount  # For gift, return the gift value
		elif self.type == 'percentage':
			return sale_line_id.price_unit * self.amount_percentage / 100
		else:
			return self.amount

	def _check_order_total_conditions(self, order_id):
		"""
		Kiểm tra điều kiện tổng giá trị và số lượng đơn hàng cho tất cả các loại promotion
		"""
		self.ensure_one()
		
		# Nếu không có điều kiện tổng giá trị và số lượng thì bỏ qua
		if self.min_amount_total <= 0 and self.min_quantity_total <= 0:
			return True
		
		order = self.env['sale.order'].browse(order_id)
		if not order:
			return False
		
		# Tính tổng giá trị và số lượng các sản phẩm áp dụng khuyến mãi
		applicable_lines = order.order_line.filtered(lambda line: self._is_product_applicable(line.product_id))
		
		total_amount = sum(line.price_unit * line.product_uom_qty for line in applicable_lines)
		total_quantity = sum(line.product_uom_qty for line in applicable_lines)
		
		# Kiểm tra điều kiện tổng giá trị (nếu được thiết lập)
		if self.min_amount_total > 0 and total_amount < self.min_amount_total:
			return False
		
		# Kiểm tra điều kiện tổng số lượng (nếu được thiết lập)
		if self.min_quantity_total > 0 and total_quantity < self.min_quantity_total:
			return False
		
		return True

	def _check_gift_qualification(self, order_id):
		"""
		Kiểm tra đơn hàng có đủ điều kiện nhận quà tặng không
		"""
		self.ensure_one()
		if self.type != 'gift' or not self.gift_product_id:
			return False
		
		order = self.env['sale.order'].browse(order_id)
		if not order:
			return False
		
		# Sử dụng hàm check chung cho đơn hàng
		return self._check_promotion_applicable_for_order(order_id)

	def _check_promotion_applicable_for_order(self, order_id):
		"""
		Kiểm tra promotion có thể áp dụng cho đơn hàng hay không.
		Logic giống như _check_promotion_applicable nhưng dành cho đơn hàng.
		"""
		self.ensure_one()
		order = self.env['sale.order'].browse(order_id)
		if not order:
			return False
		
		order_date = order.date_order.date() if order.date_order else fields.Date.today()
		if self.date_from and order_date < self.date_from:
			return False
		if self.date_to and order_date > self.date_to:
			return False
		partner_domain = self.partner_domain if self.partner_domain else False
		if partner_domain and order.partner_id not in self._get_partner_by_domain():
			return False
		
		# Kiểm tra điều kiện tổng giá trị và số lượng cho tất cả các loại promotion
		if not self._check_order_total_conditions(order_id):
			return False
		
		return True

	def _is_product_applicable(self, product_id):
		"""
		Kiểm tra sản phẩm có thuộc phạm vi áp dụng khuyến mãi không
		"""
		self.ensure_one()
		if not self.product_domain:
			return True
		try:
			product_domain = ast.literal_eval(self.product_domain)
		except Exception:
			return True
		applicable_products = self.env['product.product'].search(product_domain)
		return product_id in applicable_products

	def _apply_gift_to_order(self, order_id):
		"""
		Tạo order line quà tặng nếu chưa có và đủ điều kiện
		Hoặc xóa gift nếu không đủ điều kiện
		"""
		self.ensure_one()
		return False
		order = self.env['sale.order'].browse(order_id)
		
		# Tìm các gift lines hiện có của promotion này
		existing_gift_lines = order.order_line.filtered(lambda line: getattr(line, 'is_promotional_product', False) and line.promotion_ccv_id == self)
		
		if self._check_gift_qualification(order_id):
			# Đủ điều kiện -> tạo gift nếu chưa có
			if not existing_gift_lines:
				gift_line_values = {
					'order_id': order_id,
					'product_id': self.gift_product_id.id,
					'product_uom_qty': self.gift_quantity,
					'price_unit': 0,  # Quà tặng có giá  // Check if gift lines should be removed due to invalid quantity or disabled promotion
					'name': f'Quà tặng khuyến mãi: {self.name or ""}'
				}
				
				gift_line = self.env['sale.order.line'].create(gift_line_values)
				# Set additional fields specific to sale order line extension
				gift_line.write({
					'is_promotional_product': True,
					'promotion_ccv_id': self.id,
				})
			return True
		else:
			# Không đủ điều kiện -> xóa gift nếu có
			if existing_gift_lines:
				existing_gift_lines.unlink()
			return False

	def _remove_gift_from_order(self, order_id):
		"""
		Xóa gift lines của promotion này khỏi đơn hàng
		"""
		self.ensure_one()
		order = self.env['sale.order'].browse(order_id)
		if not order:
			return False
		
		# Tìm và xóa các gift lines của promotion này
		gift_lines_to_remove = order.order_line.filtered(lambda line: getattr(line, 'is_promotional_product', False) and line.promotion_ccv_id == self)
		if gift_lines_to_remove:
			gift_lines_to_remove.unlink()
			return True
		return False
