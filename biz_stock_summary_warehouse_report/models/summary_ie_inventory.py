from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, time, timedelta
import logging
_logger = logging.getLogger(__name__)

BATCH_SIZE = 200
COMMIT_SIZE = 100

class SummaryIEInventory(models.Model):
	_inherit = 'summary.ie.inventory'

	warehouse_id = fields.Many2one("stock.warehouse", 'Warehouse')
	warehouse_ids = fields.Many2many("stock.warehouse", string='Warehouse')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
	
	# Fields for signatures
	voter_id = fields.Many2one('res.users', string="Người lập")
	chief_finance_id = fields.Many2one('res.users', string="Phòng Kế toán")
	director_id = fields.Many2one('res.users', string="Thủ trưởng đơn vị")

	column_ids = fields.One2many(
        'summary.ie.inventory.column',
        'summary_id',
        string='Cấu hình cột',
        copy=True
    )

	@api.constrains('warehouse_id', 'warehouse_ids', 'company_id')
	def _check_company_summary(self):
		for record in self:
			if record.warehouse_id and record.warehouse_id.company_id != record.company_id:
				raise ValidationError(_('Warehouse must belong to the same company as the record.'))
			for warehouse in record.warehouse_ids:
				if warehouse.company_id != record.company_id:
					raise ValidationError(_('All warehouses must belong to the same company as the record.'))

	@api.model
	def default_get(self, fields_list):
		res = super().default_get(fields_list)
		env_params = self.env['ir.config_parameter'].sudo()
		
		# Lấy các ID từ cấu hình hệ thống
		chief_finance_id = env_params.get_param('ccv_bao_cao.chief_accountant_id', False)
		director_id = env_params.get_param('ccv_bao_cao.director_id', False)
		
		# Điền giá trị mặc định
		res.update({
			'voter_id': self.env.user.id,
			'chief_finance_id': int(chief_finance_id) if chief_finance_id else False,
			'director_id': int(director_id) if director_id else False,
		})
		
		return res

	def _prepare_domain(self):
		domain = [
			('date', '>=', datetime.combine(self.from_date, time.min) - timedelta(hours=7)),
			('date', '<=', datetime.combine(self.to_date, time.max) - timedelta(hours=7)),
			('state', '=', 'done'),
		]
		domain += [
			('product_id.detailed_type','=', 'product'),
		]
		if self.product_category_ids:
			domain += [('product_id.categ_id','in', self.product_category_ids.ids)]
		return domain

	def _prepare_warehouse_ids(self):
		warehouse_ids = self.warehouse_ids if self.warehouse_ids else self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
		return warehouse_ids

	def _prepare_stock_move(self, domain):
		stock_move = self.env['stock.move'].search(domain, order='date asc')
		return stock_move

	def action_general(self):
		self = self.sudo()
		self.line_ids.unlink()
		warehouse_ids = self._prepare_warehouse_ids()
		sms = self._prepare_stock_move(self._prepare_domain())
		vals = []

		for warehouse in warehouse_ids:
			cur_sms = sms.filtered(lambda x: x.location_id.warehouse_id == warehouse or x.location_dest_id.warehouse_id == warehouse)
			vals += self.env['summary.ie.inventory.line']._create_line(cur_sms, self, warehouse)
			
		# Fix double-counting of allocated_cost when split by warehouse
		if self.separate_warehouse_lines:
			product_totals = {}
			for val in vals:
				pid = val['product_id']
				qty = val.get('qty_import_purchase', 0) + val.get('qty_import_production', 0)
				alloc = val.get('allocated_cost', 0)
				if pid not in product_totals:
					product_totals[pid] = {'qty': 0, 'allocated_cost': alloc}
				product_totals[pid]['qty'] += qty
				if alloc > product_totals[pid]['allocated_cost']:
					product_totals[pid]['allocated_cost'] = alloc
					
			for val in vals:
				pid = val['product_id']
				qty = val.get('qty_import_purchase', 0) + val.get('qty_import_production', 0)
				if product_totals.get(pid, {}).get('qty', 0) > 0:
					val['allocated_cost'] = product_totals[pid]['allocated_cost'] * (qty / product_totals[pid]['qty'])
				else:
					val['allocated_cost'] = 0

		if not self.separate_warehouse_lines:
			new_vals = {}
			for val in vals:
				key = val['product_id']
				if key not in new_vals:
					new_vals[key] = val
				else:
					for field in self._fields:
						if self._fields[field].type in ['float', 'monetary'] and field in val and field not in ['qty_begin', 'value_begin', 'allocated_cost']:
							new_vals[key][field] += val[field]
				new_vals[key]['warehouse_id'] = False
			vals = list(new_vals.values())
		self.env['summary.ie.inventory.line'].create(vals)


	@api.model_create_multi
	def create(self, vals_list):
		records = super().create(vals_list)
		records._ensure_column_settings()
		return records

	@api.model
	def _get_column_definitions(self):
		has_val_group = self.env.user.has_group('biz_stock_summary_report.group_ie_view_quant_and_tt')
		return [
			{"code": "no", "name": "STT", "default_visible": True},
			{"code": "stock_valuation_account_id", "name": "Nhóm", "default_visible": False},
			{"code": "product_code", "name": "Mã sản phẩm", "default_visible": True},
			{"code": "product_id", "name": "Tên sản phẩm", "default_visible": True},
			{"code": "uom_id", "name": "Đơn vị tính", "default_visible": True},

			{"code": "qty_begin", "name": "Tồn đầu kỳ - Số lượng", "default_visible": True},
			{"code": "value_begin", "name": "Tồn đầu kỳ - Giá trị", "default_visible": has_val_group},

			{"code": "qty_import_purchase", "name": "Nhập mua - Số lượng", "default_visible": False},
			{"code": "value_import_purchase", "name": "Nhập mua - Giá trị", "default_visible": False},

			{"code": "qty_import_production", "name": "Nhập sản xuất - Số lượng", "default_visible": False},
			{"code": "value_import_production", "name": "Nhập sản xuất - Giá trị", "default_visible": False},

			{"code": "qty_import_inventory_adjustment", "name": "Nhập thừa kiểm kê - Số lượng", "default_visible": False},
			{"code": "value_import_inventory_adjustment", "name": "Nhập thừa kiểm kê - Giá trị", "default_visible": False},

			{"code": "qty_import_internal", "name": "Nhập nội bộ - Số lượng", "default_visible": False},
			{"code": "value_import_internal", "name": "Nhập nội bộ - Giá trị", "default_visible": False},

			{"code": "qty_import_other", "name": "Nhập khác - Số lượng", "default_visible": False},
			{"code": "value_import_other", "name": "Nhập khác - Giá trị", "default_visible": False},

			{"code": "qty_import_total", "name": "Tổng nhập - Số lượng", "default_visible": True},
			{"code": "value_import_total", "name": "Tổng nhập - Giá trị", "default_visible": has_val_group},

			{"code": "average_price", "name": "Giá bình quân", "default_visible": False},
			{"code": "allocated_cost", "name": "Giá trị phân bổ", "default_visible": False},

			{"code": "qty_export_sale", "name": "Xuất bán - Số lượng", "default_visible": False},
			{"code": "value_export_sale", "name": "Xuất bán - Doanh thu", "default_visible": False},
			{"code": "value_export_sale_cost", "name": "Xuất bán - Giá vốn", "default_visible": False},
			{"code": "value_export_sale_profit", "name": "Xuất bán - Lãi gộp", "default_visible": False},

			{"code": "qty_export_production", "name": "Xuất sản xuất - Số lượng", "default_visible": False},
			{"code": "value_export_production", "name": "Xuất sản xuất - Giá trị", "default_visible": False},

			{"code": "qty_export_inventory_adjustment", "name": "Xuất hao hụt kiểm kê - Số lượng", "default_visible": False},
			{"code": "value_export_inventory_adjustment", "name": "Xuất hao hụt kiểm kê - Giá trị", "default_visible": False},

			{"code": "qty_export_internal", "name": "Xuất nội bộ - Số lượng", "default_visible": False},
			{"code": "value_export_internal", "name": "Xuất nội bộ - Giá trị", "default_visible": False},

			{"code": "qty_export_other", "name": "Xuất khác - Số lượng", "default_visible": False},
			{"code": "value_export_other", "name": "Xuất khác - Giá trị", "default_visible": False},

			{"code": "qty_export_total", "name": "Tổng xuất - Số lượng", "default_visible": True},
			{"code": "value_export_total", "name": "Tổng xuất - Giá trị", "default_visible": has_val_group},

			{"code": "qty_end", "name": "Tồn cuối kỳ - Số lượng", "default_visible": True},
			{"code": "value_end", "name": "Tồn cuối kỳ - Giá trị", "default_visible": has_val_group},

			{"code": "warehouse_id", "name": "Kho", "default_visible": True},
		]

	def _ensure_column_settings(self):
		for record in self:
			existing_codes = set(record.column_ids.mapped('code'))
			vals_list = []
			for seq, col_def in enumerate(self._get_column_definitions(), start=1):
				if col_def["code"] in existing_codes:
					continue
				vals_list.append({
					"summary_id": record.id,
					"sequence": seq,
					"name": col_def["name"],
					"code": col_def["code"],
					"is_visible": col_def["default_visible"],
				})
			if vals_list:
				self.env['summary.ie.inventory.column'].create(vals_list)
