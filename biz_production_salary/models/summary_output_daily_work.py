# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime,timedelta
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class SummaryOfOutputForDailyWork(models.Model):
	_name = 'summary.output.daily.work'
	_description = 'Summary of output for daily work'
	_inherit = ['mail.thread', 'mail.activity.mixin', 'trp.approve']
	_order = 'id desc'

	@api.model
	def default_get(self, fields_list):
		defaults = super(SummaryOfOutputForDailyWork, self).default_get(fields_list)
		env_params = self.env['ir.config_parameter'].sudo()
		defaults.update({
			'voter_id': self.env.user.id,
			'hr_department_id': int(env_params.get_param('biz_production_salary.hr_department_id', 0)) or False,
			'chief_accountant_id': int(env_params.get_param('biz_production_salary.chief_accountant_id', 0)) or False,
			'director_id': int(env_params.get_param('biz_production_salary.director_id', 0)) or False,
		})
		return defaults

	def get_report_grouped_lines(self):
		self.ensure_one()
		grouped = {}
		for line in self.line_ids:
			date_str = line.date.strftime('%d/%m/%Y') if line.date else 'Unknown Date'
			if date_str not in grouped:
				grouped[date_str] = []
			grouped[date_str].append(line)

		result = []
		for date_str in sorted(grouped.keys(), key=lambda d: datetime.strptime(d, '%d/%m/%Y') if d != 'Unknown Date' else datetime.min):
			lines = grouped[date_str]
			totals = {
				'day_labor': sum(l.day_labor for l in lines),
				'output_pro': sum(l.output_pro for l in lines),
				'input_pro': sum(l.input_pro for l in lines),
				'other_output': sum(l.other_output for l in lines),
				'production': sum(l.production for l in lines),
				'total_quantity': sum(l.total_quantity for l in lines),
				'total_amount': sum(l.total_amount for l in lines),
			}
			result.append({
				'date_str': date_str,
				'lines': lines,
				'totals': totals
			})
		return result

	name = fields.Char('Tên', compute='_compute_name', store=True, readonly=False, tracking=True)

	@api.depends('date_from', 'date_to', 'department_id')
	def _compute_name(self):
		for rec in self:
			parts = ["Tổng hợp sản lượng công nhân"]
			if rec.department_id:
				parts.append(rec.department_id.name)
			if rec.date_from and rec.date_to:
				parts.append(f"Từ ngày {rec.date_from.strftime('%d/%m/%Y')} đến ngày {rec.date_to.strftime('%d/%m/%Y')}")
			elif rec.date_from:
				parts.append(f"Từ ngày {rec.date_from.strftime('%d/%m/%Y')}")
			elif rec.date_to:
				parts.append(f"Đến ngày {rec.date_to.strftime('%d/%m/%Y')}")

			rec.name = " - ".join(parts)

	date_from = fields.Date('Date From',required=True)
	date_to = fields.Date('Date To',required=True)
	line_ids = fields.One2many('summary.output.spreadsheet','summary_id',string="Summary of output spreadsheet")
	line_1_ids = fields.One2many('total.amount.received.byday','summary_id',string="Total amount received by day")
	line_2_ids = fields.One2many('final.total','summary_id',string="Final Total")
	department_id = fields.Many2one('hr.department',string="Department",required=True)
	date_of_last_contract_push = fields.Datetime('Date of last contract push',copy=False)
	currency_id = fields.Many2one('res.currency',string="Currency",default=lambda self: self.env.company.currency_id)

	voter_id = fields.Many2one('res.users', string="Người lập biểu", default=lambda self: self.env.user)
	loading_department_id = fields.Many2one('res.users', string="Bộ phận bốc xếp")
	hr_department_id = fields.Many2one('res.users', string="Phòng HCNS")
	chief_accountant_id = fields.Many2one('res.users', string="Kế toán trưởng")
	director_id = fields.Many2one('res.users', string="Ban lãnh đạo")

	state = fields.Selection(
		[('draft', 'Nháp'), ('approve', 'Đang duyệt'), ('approved', 'Đã duyệt'), ('refuse', 'Từ chối'), ('cancel', 'Hủy')],
		'Trạng thái', default='draft', tracking=True)

	trp_approve_history_ids = fields.One2many('trp.approve.history', 'summary_output_daily_work_id', string='Lịch sử duyệt', copy=False)

	@api.depends('trp_approve_config_line_id', 'trp_approve_config_line_id.manager_type',
				 'trp_approve_config_line_id.user_ids', 'trp_approve_config_line_id.job_ids',
				 'voter_id', 'loading_department_id', 'hr_department_id', 'chief_accountant_id', 'director_id')
	def _compute_current_approve_users(self):
		super(SummaryOfOutputForDailyWork, self)._compute_current_approve_users()
		for record in self:
			cfg = record.trp_approve_config_line_id
			if cfg:
				approver_ids = record.current_approve_user_ids.ids
				if cfg.manager_type == 'creator':
					if record.voter_id:
						approver_ids.append(record.voter_id.id)
				elif cfg.manager_type == 'loading_salary':
					if record.loading_department_id:
						approver_ids.append(record.loading_department_id.id)
				record.current_approve_user_ids = [(6, 0, list(set(approver_ids)))]

	@api.onchange('department_id')
	def _onchange_department_ids(self):
		for rec in self:
			if rec.department_id:
				emp = self.env['hr.employee'].search(
					[('department_id', '=', rec.department_id.id)], limit=1)
				rec.loading_department_id = emp.parent_id.user_id if emp and emp.parent_id else False

	def unlink(self):
		for record in self:
			if record.state not in ['refuse', 'cancel', 'draft'] and not self.env.user.has_group('base.group_system'):
				raise UserError(_('Bạn chỉ có thể xoá báo cáo ở trạng thái Nháp, Từ chối hoặc Hủy!'))
		return super(SummaryOfOutputForDailyWork, self).unlink()

	def action_cancel(self):
		self.write({'state': 'cancel'})
		res_history = self.trp_approve_history_ids
		self.env['mail.activity'].search([('trp_approve_history_id', 'in', res_history.ids)]).with_context(skip_approve_done=True).action_done()

	def action_refuse(self):
		if self.trp_approve_history_ids:
			self.write({'state': 'refuse'})

	def action_print_pdf(self):
		return self.env.ref('biz_production_salary.action_report_salary_by_production_pdf').report_action(self)

	def action_print_excel(self):
		return self.env.ref('biz_production_salary.action_report_salary_by_production_xlsx').report_action(self)

	def action_undo(self):
		self.write({'state': 'draft'})

	def action_sign(self):
		self = self.sudo()
		res_approve = {}
		if not self.trp_approve_config_line_id and self.state in ('draft'):
			self.approve_next_action = 'action_sign'
			self.approve_state_init = self.state
			self.approve_state_next = 'approve'
			res_approve = self.with_context(approve_type='new').create_approve()
		if not res_approve or not self.trp_approve_config_line_id:
			if self.state == 'approve':
				self.update({'state': 'approved'})
				return

	def action_agree(self):
		res = super(SummaryOfOutputForDailyWork, self).action_agree()
		for record in self:
			if record.state == 'approved':
				record.message_post(body=f"Báo cáo tổng hợp sản lượng công nhân {record._get_html_link()} đã được duyệt.")
		return res

	def name_get(self):
		result = []
		for inv in self:
			result.append((inv.id, _("Summary of output for daily work")))
		return result

	def push_up_contract(self):
		HrAllowance = self.env['hr.allowance'].sudo()
		HrContract = self.env['hr.contract'].sudo()

		# Tính toán Năm và Tháng từ trường date_from trên form view
		year = int(self.date_from.strftime('%Y'))
		month = str(int(self.date_from.strftime('%m')))

		for line in self.line_2_ids:
			contracts = HrContract.search([
				('employee_id', '=', line.employee_id.id),
				('state', '=', 'open')
			])
			for contract in contracts:
				# Xóa các bản ghi hiện có trên hợp đồng của bảng Phụ cấp hàng tháng nếu trùng năm, tháng và có mã là 'LSX'
				allowance_month = contract.allowance_month_ids.filtered(
					lambda x: x.year == year and x.month == month and x.code == 'LSX'
				)
				if allowance_month:
					allowance_month.unlink()

				# Tìm kiếm trong cấu hình Các khoản phụ cấp; nếu kh tìm thấy bản ghi nào có tên là 'Lương sản xuất' và mã là 'LSX' thì tạo mới
				allowance_id = HrAllowance.search([
					('name', '=', 'Lương sản xuất'),
					('code', '=', 'LSX')
				], limit=1)
				if not allowance_id:
					allowance_id = HrAllowance.create({
						'name': 'Lương sản xuất',
						'code': 'LSX',
						'is_fixed': True
					})

				# Thêm bản ghi mới vào trong bảng Phụ cấp hàng tháng trên hợp đồng
				allowance_vals = {
					'amount': line.amount_received,
					'allowance_id': allowance_id.id,
					'year': year,
					'month': month,
					'code': 'LSX'
				}
				contract.write({'allowance_month_ids': [(0, 0, allowance_vals)]})
		#Update ngày cập nhật gần nhất lên hợp đồng khi bấm nút đẩy lên hợp đồng
		self.date_of_last_contract_push = datetime.now()

	def action_summary(self):
		# Xóa các bảng hiện tại
		self.line_ids.unlink()
		self.line_1_ids.unlink()
		self.line_2_ids.unlink()

		# Khai báo
		StockMove = self.env['stock.move'].sudo()
		SummaryCommon = self.env['summary.common'].sudo()
		Employee = self.env['hr.employee'].sudo()

		date_from = datetime.combine(self.date_from, datetime.min.time()) - timedelta(hours=7)
		date_to = datetime.combine(self.date_to, datetime.max.time()) - timedelta(hours=7)
		# Domain
		domain_move = [
			('state', '=', 'done'),
			'|',
			'&','&',
			('picking_id.stock_date_receipt', '>=', date_from),
			('picking_id.stock_date_receipt', '<=', date_to),
			'|', ('picking_id.employee_ids', '!=', False), ('picking_id.department_ids', '!=', False),
			'&','&',
			('production_id.stock_date_receipt', '>=', date_from),
			('production_id.stock_date_receipt', '<=', date_to),
			'|', ('production_id.employee_ids', '!=', False), ('production_id.department_ids', '!=', False),
			'|', '|',
			('picking_type_id.apply_unit_pirce_cal_output_worker', '=', True),
			('picking_type_id.apply_unit_price_goods_sold', '=', True),
			('picking_type_id.apply_unit_price_goods_imported', '=', True),
		]
		moves = StockMove.search(domain_move)

		merge_data = {}

		def get_employee_enjoys(record, filter_ids=None, employees_choose=False):
			"""
			Trả về danh sách các dict có thông tin về nhân viên cho một bản ghi nhất định.
			Tùy chọn lọc ra những nhân viên có ID nằm trong filter_ids.
			Nếu employees_choose được cung cấp, hãy sử dụng bản ghi đó thay vì tìm kiếm theo phòng ban.
			"""
			filter_ids = filter_ids or []
			values = []
			date = record.date
			if record._name == 'stock.move':
				date = (record.picking_id and (record.picking_id.stock_date_receipt + timedelta(hours=7)).date()) \
					or (record.production_id and (record.production_id.stock_date_receipt + timedelta(hours=7)).date())
			if not employees_choose:
				employees = self.env['hr.employee'].sudo().search([('department_id', '=', self.department_id.id)])
			else:
				employees = employees_choose
			for emp in employees.filtered(lambda e: e.id not in filter_ids):
				coefficient = self.env['change.manual.worker.coefficient.byday'].search([('date', '=', date), ('employee_ids', '=', emp.id)]).coefficient or 0
				em_coefficient = emp.worker_coefficient
				working_day = SummaryCommon.search([
					('employee_id', '=', emp.id),
					('summary_id.month', '=', date.strftime('%m')),
					('summary_id.year', '=', date.strftime('%Y'))
				], limit=1)
				if working_day and coefficient == 0:
					check_date = working_day['date_%s' % int(date.strftime('%d'))]
					mapping = {
						None: 0,
						"": 0,
						"X": 1,
						"X/2": 0.5,
						"P/2": 0.5,
					}
					coefficient = em_coefficient * mapping.get(check_date, 0)
				values.append({
					'date': date,
					'employee_id': emp.id,
					'rate': coefficient,
				})
			return values

		# Xử lý từng đợt di chuyển kho (hoặc picking hoặc đang production)
		for move in moves.filtered(lambda m: m.picking_id or m.production_id):
			move_filter = move.picking_id or move.production_id
			stock_date_receipt = move_filter.stock_date_receipt + timedelta(hours=7)
			# Lọc theo phòng ban: nếu employee_ids tồn tại, hãy kiểm tra phòng ban của họ;
			# nếu không, hãy kiểm tra trực tiếp department_ids.
			if move_filter.employee_ids:
				if self.department_id not in move_filter.employee_ids.mapped('department_id'):
					continue
			else:
				if self.department_id.id not in move_filter.department_ids.ids:
					continue

			# Tạo khóa hợp nhất dựa trên sản phẩm, ngày và loại picking_type_id.
			merge_key = '%s-%s-%s' % (move.product_id, stock_date_receipt.strftime('%Y-%m-%d'), move.picking_type_id)

			# Xác định giá đơn vị dựa trên cài đặt trong picking_type_id.
			price_unit = 0
			if move.picking_type_id.apply_unit_pirce_cal_output_worker:
				if move_filter._name == 'mrp.production' and move.production_id.bom_id and move.production_id.bom_id.unit_price_cal_out_worker != 0:
					price_unit = move.production_id.bom_id.unit_price_cal_out_worker
				else:
					price_unit = move.product_id.unit_price_cal_out_worker or 0
			if move.picking_type_id.apply_unit_price_goods_sold:
				price_unit = move.product_id.unit_price_export or 0
			if move.picking_type_id.apply_unit_price_goods_imported:
				price_unit = move.product_id.unit_price_import or 0

			# Điều chỉnh số lượng bằng cách chia cho nhân viên hoặc phòng ban nếu có thể.
			quantity_done = move.quantity_done
			employee_choice_flag = False
			if move_filter:
				if move_filter.employee_ids:
					employee_choice_flag = True
					merge_key = move_filter  # thay thế khóa hợp nhất nếu employee_ids tồn tại
				elif move_filter.department_ids:
					try:
						quantity_done /= len(move_filter.department_ids)
					except ZeroDivisionError:
						quantity_done = 0

			# Nếu khóa hợp nhất không tồn tại, hãy tạo một mục mới.
			if merge_key not in merge_data:
				employee_enjoys_ids = get_employee_enjoys(move, employees_choose=move_filter.employee_ids if employee_choice_flag else False)
				merge_data[merge_key] = {
					'date': stock_date_receipt,
					'product_id': move.product_id.id,
					'picking_type_id': move.picking_type_id.id,
					'output_pro': quantity_done if move.picking_type_id.code == 'outgoing' else 0,
					'output_move_ids': [move.id] if move.picking_type_id.code == 'outgoing' else [],
					'input_pro': quantity_done if move.picking_type_id.code in ['incoming', 'internal'] else 0,
					'intput_move_ids': [move.id] if move.picking_type_id.code in ['incoming', 'internal'] else [],
					'production': quantity_done if move.picking_type_id.code == 'mrp_operation' else 0,
					'production_move_ids': [move.id] if move.picking_type_id.code == 'mrp_operation' else [],
					'price_unit': price_unit,
					'employee_enjoys_ids': employee_enjoys_ids if employee_enjoys_ids else [],
				}
			else:
				# Cập nhật mục nhập hợp nhất hiện có dựa trên mã trong picking_type_id.
				if move.picking_type_id.code == 'outgoing':
					merge_data[merge_key]['output_move_ids'].append(move.id)
					merge_data[merge_key]['output_pro'] += quantity_done
				if move.picking_type_id.code in ['incoming', 'internal']:
					merge_data[merge_key]['intput_move_ids'].append(move.id)
					merge_data[merge_key]['input_pro'] += quantity_done
				if move.picking_type_id.code == 'mrp_operation':
					merge_data[merge_key]['production_move_ids'].append(move.id)
					merge_data[merge_key]['production'] += move.quantity_done

				#Cập nhật nhân viên hưởng đồng thời tránh trùng lặp.
				existing_employee_ids = [emp.get('employee_id') for emp in merge_data[merge_key]['employee_enjoys_ids']]
				new_employee_enjoys = get_employee_enjoys(move, filter_ids=existing_employee_ids)
				merge_data[merge_key]['employee_enjoys_ids'] += new_employee_enjoys

		# Xử lý Công nhật
		CongNhat = self.env['enter.daily.work.output.other'].sudo()
		domain_congnhat = [
			('date', '>=', self.date_from),
			('date', '<=', self.date_to),
			'|', ('employee_ids', '!=', False), ('department_ids', '!=', False)
		]
		congnhat = CongNhat.search(domain_congnhat)

		for cn in congnhat.filtered(lambda c: self.department_id in c.employee_ids.mapped('department_id')
									  or self.department_id.id in c.department_ids.ids):
			merge_key = '%s-%s-%s' % (cn.product_id, cn.date, cn.price_unit)
			production_other = cn.production_other or 0
			day_labor = cn.day_labor_id.day_labor_coefficient if cn.day_labor_id else 0
			employees_congnhat = cn.employee_ids + Employee.search([('department_id','in',cn.department_ids.ids)])
			if merge_key not in merge_data:
				employee_enjoys_ids = get_employee_enjoys(cn,employees_choose=employees_congnhat)
				merge_data[merge_key] = {
					'date': cn.date,
					'product_id': cn.product_id.id,
					'other_output': production_other,
					'day_labor': day_labor,
					'employee_enjoys_ids': employee_enjoys_ids if employee_enjoys_ids else [],
					'price_unit': cn.price_unit,
				}
			else:
				merge_data[merge_key]['other_output'] += production_other
				merge_data[merge_key]['day_labor'] += day_labor

				existing_employee_ids = [emp.get('employee_id') for emp in merge_data[merge_key]['employee_enjoys_ids']]
				new_employee_enjoys = get_employee_enjoys(cn, filter_ids=existing_employee_ids,employees_choose=employees_congnhat)
				merge_data[merge_key]['employee_enjoys_ids'] += new_employee_enjoys

		# Tính toán cuối cùng: tính tổng số tiền và update lại các giá trị
		final_lines = []
		for key, rec in merge_data.items():
			# Thêm liên kết
			rec['employee_enjoys_ids'] = [(0, 0, emp) for emp in rec.get('employee_enjoys_ids')] if rec.get('employee_enjoys_ids') else False
			rec['output_move_ids'] = [(6, 0, rec['output_move_ids'])] if rec.get('output_move_ids') else False
			rec['intput_move_ids'] = [(6, 0, rec['intput_move_ids'])] if rec.get('intput_move_ids') else False
			rec['production_move_ids'] = [(6, 0, rec['production_move_ids'])] if rec.get('production_move_ids') else False

			final_lines.append((0, 0, rec))
		self.line_ids = final_lines

		arr_date = list(set(self.line_ids.mapped('date')))
		arr_employee_id = list(set([line.id for line in self.line_ids.mapped('employee_enjoys_ids.employee_id')]))

		line1 = []
		for employee_id in arr_employee_id:
			for date in arr_date:
				line1.append((0, 0, {'production_date': date, 'employee_id': employee_id}))
		self.line_1_ids = line1
		
		self.line_2_ids = [(0, 0, {'employee_id': line,}) for line in arr_employee_id]

	def action_view_line_ids(self):
		action = self.env.ref('biz_production_salary.action_summary_output_spreadsheet').sudo().read()[0]
		action['domain'] = [('summary_id', '=', self.id)]
		return action

	def action_view_line_1_ids(self):
		action = self.env.ref('biz_production_salary.action_total_amount_received_byday').sudo().read()[0]
		action['domain'] = [('summary_id', '=', self.id)]
		return action

	def action_view_line_2_ids(self):
		action = self.env.ref('biz_production_salary.action_final_total').sudo().read()[0]
		action['domain'] = [('summary_id', '=', self.id)]
		return action
