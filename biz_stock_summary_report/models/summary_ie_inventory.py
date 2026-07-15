from odoo import api, fields, models, _
from odoo.fields import Command
from datetime import datetime, time, timedelta
import logging
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class SummaryIEInventory(models.Model):
	_name = 'summary.ie.inventory'
	_description = 'Summary of import and export inventory'
	
	name = fields.Char('Tên báo cáo')
	previous_period_id = fields.Many2one('summary.ie.inventory', 'Previous period')		
	from_date = fields.Date('From date', required=True)
	to_date = fields.Date('To date', required=True)
	state = fields.Selection([
			('new','New'),
			('locked','Locked'),
		], string='State', default='new')
	currently_there_are_no_products_available = fields.Boolean('Currently there are no products available')
	product_category_ids = fields.Many2many('product.category',string="Product Category")
	separate_warehouse_lines = fields.Boolean('Tách dòng theo kho', default=True, 
		help='Nếu chọn: mỗi dòng hiển thị cho 1 kho riêng biệt. Nếu không chọn: mỗi dòng hiển thị tổng của tất cả kho')
	line_ids = fields.One2many('summary.ie.inventory.line', 'summary_id', 'Details')

	@api.constrains('separate_warehouse_lines')
	def _check_separate_warehouse_lines(self):
		for record in self:
			if record.separate_warehouse_lines and record.previous_period_id and record.previous_period_id.separate_warehouse_lines != record.separate_warehouse_lines:
				raise ValidationError("Không thể chuyển đổi trạng thái tách dòng theo kho khi đã có báo cáo trước đó.")

	def name_get(self):
		result = []
		for group in self:
			from_date = group.from_date.strftime('%d/%m/%Y')
			to_date = group.to_date.strftime('%d/%m/%Y')
			name = '%s - %s - %s' % (group.name if group.name else '', from_date if from_date else '', to_date if to_date else '')
			result.append((group.id, name))
		return result

	def action_general(self):
		pass
		
	def action_lock(self):
		self.write({
			'state': 'locked'
		})

	def action_unlock(self):
		self.write({
			'state': 'new'
		})

	def action_view_detail(self):
		action = self.env.ref('biz_stock_summary_report.action_summary_ie_inventory_line').sudo().read()[0]
		action['domain'] = [('summary_id', '=', self.id)]
		return action
