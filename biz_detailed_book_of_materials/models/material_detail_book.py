# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, time
from odoo.tools import html2plaintext
import logging

_logger = logging.getLogger(__name__)

FIELDS = [
	'product_code',"product_name","accounting_date",
	"document_number","explain","uom_id","qty_import","qty_export","qty_inv",'account_warehouse_code',
	'ctp_account_ids','partner_id','factory_manager_name','production_id','warehouse_id'
]

class MaterialDetailBook(models.Model):
	_name = 'material.detail.book'
	_description = 'Material detail book'
	_inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
	_order = 'id desc'

	name = fields.Char('Tên phiếu', compute='_compute_name', store=True)

	from_date = fields.Date('From date', required=True)
	to_date = fields.Date('To date', required=True)
	warehouse_ids = fields.Many2many("stock.warehouse", string='Warehouse')
	product_ids = fields.Many2many("product.product", string='Sản phẩm')
	warehouse_id = fields.Many2one("stock.warehouse", 'Warehouse')
	initial_balance = fields.Float("Initial balance")
	previous_period_id = fields.Many2one('material.detail.book', 'Previous period')
	line_ids = fields.One2many('material.detail.book.line', 'material_id', 'Details')

	# Người ký
	voter_id = fields.Many2one('res.users', string='Người lập phiếu',
							   default=lambda s: s.env.user)
	warehouse_manager_id = fields.Many2one('res.users', string='Thủ Kho/Nhà Máy')
	stock_controller_id = fields.Many2one('res.users', string='Chuyên viên kiểm soát kho')
	chief_acc_id = fields.Many2one('res.users', string='Phòng kế toán')
	hcns_id = fields.Many2one('res.users', string='Phòng HCNS')
	unit_heads_id = fields.Many2one('res.users', string='Thủ trưởng đơn vị')
	export_fields_ids = fields.One2many("material.detail.book.fields", 'material_id', 'Export fields', compute="compute_fields_export", store=True, readonly=False)

	state = fields.Selection(
		[('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'),
		 ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
		string='Trạng thái', default='draft', tracking=True)

	trp_approve_history_ids = fields.One2many(
		'trp.approve.history', 'material_detail_book_id',
		string='Lịch sử duyệt', copy=False)

	is_user_current = fields.Boolean(compute='_compute_is_user_current')

	@api.depends('current_approve_user_ids')
	def _compute_is_user_current(self):
		for rec in self:
			if not rec.current_approve_user_ids:
				rec.is_user_current = True
			else:
				rec.is_user_current = self.env.user in rec.current_approve_user_ids

	@api.depends('warehouse_ids', 'from_date', 'to_date')
	def _compute_name(self):
		for rec in self:
			wh_names = ', '.join(rec.warehouse_ids.mapped('name')) or 'Tất cả kho'
			from_str = rec.from_date.strftime('%d/%m/%Y') if rec.from_date else ''
			to_str = rec.to_date.strftime('%d/%m/%Y') if rec.to_date else ''
			date_range = ' - '.join(filter(None, [from_str, to_str]))
			rec.name = '%s | %s' % (wh_names, date_range) if date_range else wh_names

	@api.depends("create_date",'from_date','to_date')
	def compute_fields_export(self):
		Field = self.env['ir.model.fields'].sudo().with_context(active_test=False)
		for res in self:
			if not res.export_fields_ids:
				for field in FIELDS:
					field_id = Field._get('material.detail.book.line', field)
					res.export_fields_ids = [(0,0, { 'field_id': field_id.id })]

	@api.model
	def default_get(self, fields_list):
		defaults = super().default_get(fields_list)
		env_params = self.env['ir.config_parameter'].sudo()
		stock_controller_id = env_params.get_param('biz_detailed_book_of_materials.stock_controller_id', False)
		warehouse_manager_id = env_params.get_param('biz_detailed_book_of_materials.warehouse_manager_id', False)
		chief_acc_id = env_params.get_param('biz_detailed_book_of_materials.chief_acc_id', False)
		hcns_id = env_params.get_param('biz_detailed_book_of_materials.hcns_id', False)
		unit_heads_id = env_params.get_param('biz_detailed_book_of_materials.unit_heads_id', False)
		defaults.update({
			'voter_id': self.env.user.id,
			'stock_controller_id': int(stock_controller_id) if stock_controller_id else False,
			'warehouse_manager_id': int(warehouse_manager_id) if warehouse_manager_id else False,
			'chief_acc_id': int(chief_acc_id) if chief_acc_id else False,
			'hcns_id': int(hcns_id) if hcns_id else False,
			'unit_heads_id': int(unit_heads_id) if unit_heads_id else False,
		})
		return defaults

	def action_view_detail(self):
		action = self.env.ref('biz_detailed_book_of_materials.action_material_detail_book_line').sudo().read()[0]
		action['domain'] = [('material_id', '=', self.id)]
		return action

	# ------------------------------------------------------------
	# Quy trình duyệt
	# ------------------------------------------------------------
	def action_sign(self):
		self = self.sudo()
		if not self.line_ids:
			raise UserError(_("Vui lòng tổng hợp dữ liệu trước khi trình duyệt!"))
		res_approve = {}
		if not self.trp_approve_config_line_id and self.state == 'draft':
			self.approve_next_action = 'action_sign'
			self.approve_state_init = self.state
			self.approve_state_next = 'approve'
			res_approve = self.with_context(approve_type='new').create_approve()
		if not res_approve or not self.trp_approve_config_line_id:
			if self.state in ('draft', 'approve'):
				self.update({'state': 'approved'})

	def action_cancel(self):
		self.write({'state': 'cancel'})
		res_history = self.trp_approve_history_ids
		self.env['mail.activity'].search([('trp_approve_history_id', 'in', res_history.ids)]) \
			.with_context(skip_approve_done=True).action_done()

	def action_undo(self):
		self.write({'state': 'draft'})

	def unlink(self):
		for record in self:
			if not self.env.user.has_group('base.group_system') and record.state not in ('draft', 'refuse', 'cancel'):
				raise UserError(_("Không thể xóa phiếu đã/đang duyệt!"))
		return super().unlink()

	def name_get(self):
		result = []
		for res in self:
			name = '%s - %s' % (res.from_date.strftime('%d/%m/%Y'), res.to_date.strftime('%d/%m/%Y'))
			result.append((res.id, name))
		return result

	def _prepare_domain(self):
		domain = [
			('date', '>=', datetime.combine(self.from_date, time.min) - timedelta(hours=7)),
			('date', '<=', datetime.combine(self.to_date, time.max) - timedelta(hours=7)),
			('state', '=', 'done'),
		]
		if self.product_ids:
			domain += [
				('product_id', 'in', self.product_ids.ids)
			]
		return domain

	def action_general(self):
		"""
		Process stock valuation layers for the specified date range and warehouses,
		group the data by product and warehouse, and create valuation lines accordingly.
		"""
		self = self.sudo()
		self.line_ids.unlink()

		warehouse_ids = self.warehouse_ids if self.warehouse_ids else self.env['stock.warehouse'].search([])


		# Initialize grouping dictionary
		groups = {}
		for warehouse in warehouse_ids:
			domain = self._prepare_domain()
			domain += [
				'|',
				('location_id.warehouse_id', '=', warehouse.id),
				('location_dest_id.warehouse_id', '=', warehouse.id),
			]
			sms = self.env['stock.move'].search(domain, order="date, product_id")

			for sm in sms:
				if sm.picking_id and sm.picking_id.mrp_production_id and sm.picking_id.location_id.warehouse_id == sm.picking_id.location_dest_id.warehouse_id:
					continue
				account_id = sm.account_id
				account_dest_id = sm.account_dest_ids
				is_in = sm.location_id.warehouse_id != warehouse
				production = sm.production_id or sm.raw_material_production_id or sm.unbuild_id.mo_id or sm.consume_unbuild_id.mo_id
				description = self.get_description(sm, production)
				valuation_line = self.build_valuation_line(sm, account_id, account_dest_id, production, description, warehouse, is_in=is_in)
				group_key = (sm.product_id, warehouse)
				child_line_key = (sm.id, True)
				self.update_group(groups, group_key, child_line_key, valuation_line)
				if sm.location_id.warehouse_id == sm.location_dest_id.warehouse_id:
					description = self.get_description(sm, production)
					valuation_line = self.build_valuation_line(sm, account_id, account_dest_id, production, description, warehouse, is_in=not is_in)
					child_line_key = (sm.id, False)
					self.update_group(groups, group_key, child_line_key, valuation_line)

		# Build line_ids with group summary and detail lines
		self.process_final_lines(groups)

	def get_description(self, stock_move, production):
		"""Determine description from picking or production"""
		description = ''
		if stock_move.picking_id:
			description = stock_move.picking_id.reason_output_input_stock or ''
		elif production:
			description = production.interpretation or ''
		return description

	def build_valuation_line(self, stock_move, account_id, account_dest_id, production, description, warehouse, is_in=False):
		"""Build the valuation line dictionary"""
		qty = stock_move.quantity_done
		if qty and stock_move.product_uom != stock_move.product_id.uom_id:
			qty = stock_move.product_uom._compute_quantity(qty, stock_move.product_id.uom_id)
		return {
			'product_id': stock_move.product_id.id,
			'accounting_date': stock_move.date + timedelta(hours=7),
			'document_number': stock_move.reference or '',
			'explain': html2plaintext(description),
			'uom_id': stock_move.product_id.uom_id.id if stock_move.product_id.uom_id else False,
			'qty_import': qty if is_in else 0,
			'qty_export': qty if not is_in else 0,
			'account_warehouse_id': account_id.id or False,
			'ctp_account_ids': [(6, 0, account_dest_id.ids)] if account_dest_id else False,
			'partner_id': (stock_move.picking_id.sudo().partner_id.id
						if stock_move.picking_id and stock_move.picking_id.sudo().partner_id
						else False),
			'production_id': production.id or False,
			'warehouse_id': warehouse.id or False,
			'is_import': is_in,
			'is_export': not is_in,
		}

	def update_group(self, groups, group_key, child_line_key, valuation_line):
		"""Update group dictionary with valuation line"""
		if group_key not in groups:
			groups[group_key] = {
				'initial_balance': self.get_initial_balance(group_key[0], group_key[1]),
				'lines': {child_line_key: valuation_line},
			}
		else:
			groups[group_key]['lines'][child_line_key] = valuation_line

	def process_final_lines(self, groups):
		"""Process final group lines and build line_ids"""
		for group_key, group_vals in groups.items():
			initial_balance = group_vals['initial_balance']
			self.line_ids = [(0, 0, {
				'product_id': group_key[0].id if group_key[0] else False,
				'warehouse_id': group_key[1].id if group_key[1] else False,
				'is_total': True,
				'qty_inv': initial_balance,
			})]

			# Process each child line
			for line in sorted(group_vals['lines'].values(), key=lambda item: (item['accounting_date'], -abs(item['qty_import']))):
				line['qty_import'] = abs(line['qty_import'])
				line['qty_export'] = abs(line['qty_export'])
				initial_balance = initial_balance + line['qty_import'] - line['qty_export']
				line['qty_inv'] = initial_balance
				if not line['qty_import'] and not line['qty_export']:
					continue
				self.line_ids = [(0, 0, line)]

	def get_report_pdf_data(self):
		self = self.sudo()
		groups = {}
		for line in self.line_ids.filtered(lambda x: not x.is_total):
			line = line.sudo()
			warehouse_id = line.warehouse_id
			if warehouse_id not in groups:
				groups[warehouse_id] = {}
			prod = groups[warehouse_id].setdefault(line.product_id, {
				'sum_import': 0,
				'sum_export': 0,
				'lines': []
			})
			prod['sum_import'] += line.qty_import
			prod['sum_export'] += line.qty_export
			prod['lines'].append({
				'product_code': line.product_code or '',
				"product_name": line.product_id.name or '',
				"accounting_date": line.accounting_date,
				"document_number": line.document_number or '',
				"explain": line.explain or '',
				"uom_id": line.uom_id.name or '',
				"qty_import": round(line.qty_import, 3),
				"qty_export": round(line.qty_export, 3),
				"qty_inv": line.qty_inv,
				'account_warehouse_code': line.account_warehouse_code or '',
				'ctp_account_ids': line.ctp_account_ids and ','.join(line.ctp_account_ids.mapped('code')) or '',
				'partner_id': line.object_name or '',
				'production_id': line.production_id.name or '',
				'warehouse_id': line.warehouse_id.name or '',
				'factory_manager_name': line.factory_manager_name or ''
			})

		warehouses = []
		total_import = total_export = 0
		total_lines = 0
		for warehouse, product_ids in groups.items():
			wh_lines_count = sum(len(ln['lines']) for ln in product_ids.values())
			total_lines += wh_lines_count
			products = []
			for product_id, vals in product_ids.items():
				lines = sorted(vals['lines'], key=lambda x: x['accounting_date'] or datetime.date.min)
				sum_import = vals['sum_import']
				sum_export = vals['sum_export']
				total_import += sum_import
				total_export += sum_export
				initial_balance = self.get_initial_balance(product_id, warehouse)
				last_qty_inv = lines[-1]['qty_inv'] if lines else initial_balance
				products.append({
					'name': product_id.name or '',
					'default_code': product_id.default_code or '',
					'lines_count': len(lines),
					'initial_balance': initial_balance,
					'sum_import': sum_import,
					'sum_export': sum_export,
					'last_qty_inv': last_qty_inv,
					'lines': lines,
				})
			warehouses.append({
				'name': warehouse.name or '',
				'lines_count': wh_lines_count,
				'products': products,
			})
		return {
			'warehouses': warehouses,
			'total_import': round(total_import, 3),
			'total_export': round(total_export, 3),
			'total_lines': total_lines,
		}

	def get_initial_balance(self, product_id, warehouse_id):
		if not self.previous_period_id or not product_id or not warehouse_id:
			return 0

		line = self.env['material.detail.book.line'].search([
				('product_id','=', product_id.id),
				('warehouse_id','=',warehouse_id.id),
				('is_total','=', False),
				('material_id','=', self.previous_period_id.id)
			])
		if not line:
			return self.previous_period_id.get_initial_balance(product_id,warehouse_id)
		return line[-1:].qty_inv

class MaterialDetailBookLine(models.Model):
	_name = 'material.detail.book.line'
	_description = 'Details'

	material_id = fields.Many2one("material.detail.book", ondelete='cascade')
	product_code = fields.Char("Product code", related="product_id.default_code")
	product_id = fields.Many2one("product.product", 'Product')	
	product_name = fields.Char("Product name", related='product_id.name')
	accounting_date = fields.Date("Accounting date")
	document_number = fields.Char("Document number")
	explain = fields.Text("Explain")
	uom_id = fields.Many2one('uom.uom','Uom')
	qty_import = fields.Float("Quantity import",digits=(16, 3))
	qty_export = fields.Float("Quantity export",digits=(16, 3))
	qty_inv = fields.Float("Quantity inventory",digits=(16, 3))
	account_warehouse_id = fields.Many2one("account.account",'Warehouse account')
	account_warehouse_code = fields.Char('Warehouse account', related="account_warehouse_id.code")
	ctp_account_ids = fields.Many2many("account.account", string='Countered Accounts')
	partner_id = fields.Many2one("res.partner",'Partner')
	object_name = fields.Char(compute="_compute_partner_name",string='Object name')
	production_id = fields.Many2one("mrp.production",'Production')
	warehouse_id = fields.Many2one("stock.warehouse", 'Warehouse')
	is_total = fields.Boolean("Is total")
	is_import = fields.Boolean("Is Import")
	is_export = fields.Boolean("Is Export")
	stock_valuation_layer_id = fields.Many2one('stock.valuation.layer',string="Stock Valuation Layer")
	factory_manager_name = fields.Char(compute="_compute_factory_manager_name", string="Factory Manager")

	@api.depends('partner_id','production_id')
	def _compute_partner_name(self):
		for rec in self:
			object_name = ''
			if rec.partner_id:
				object_name = rec.partner_id.sudo().name
			elif rec.production_id:
				object_name = rec.production_id.user_id.name_without_position
			rec.object_name = object_name

	@api.depends('production_id')
	def _compute_factory_manager_name(self):
		for rec in self:
			if rec.production_id and rec.production_id.user_id:
				rec.factory_manager_name = rec.production_id.user_id.name_without_position
			else:
				rec.factory_manager_name = ''
	
	def action_open_reference(self):
		action_mrp = self.env.ref('mrp.mrp_production_action').sudo().read()[0]
		action_picking = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
		if self.production_id:
			action_mrp['res_id'] = self.production_id.id
			action_mrp['view_mode'] = 'form'
			action_mrp['views'] = [(False, 'form')]
			return action_mrp
		svl = self.stock_valuation_layer_id
		if svl:
			stock_move = svl.stock_move_id
			picking = stock_move.picking_id
			if picking:
				action_picking['res_id'] = picking.id
				action_picking['view_mode'] = 'form'
				action_picking['views'] = [(False, 'form')]
				return action_picking
		name = self.document_number
		if name:
			picking = self.env['stock.picking'].sudo().search([('name', '=', name)])
			if picking:
				action_picking['res_id'] = picking.id
				action_picking['view_mode'] = 'form'
				action_picking['views'] = [(False, 'form')]
				return action_picking
			mrp = self.env['mrp.production'].sudo().search([('name', '=', name)])
			if mrp:
				action_mrp['res_id'] = mrp.id
				action_mrp['view_mode'] = 'form'
				action_mrp['views'] = [(False, 'form')]
				return action_mrp
		return False

class MaterialDetailBookFieldExport(models.Model):
	_name = 'material.detail.book.fields'
	_description ="Fields export"
	_order = 'sequence,id'

	sequence = fields.Integer(default=1)
	material_id = fields.Many2one("material.detail.book", ondelete='cascade')
	field_id = fields.Many2one("ir.model.fields", 'Fields')
	is_selected = fields.Boolean('Selected', default=True)
