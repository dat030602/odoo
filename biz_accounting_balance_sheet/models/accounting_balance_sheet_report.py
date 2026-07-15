# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

class AccountingBalanceSheetReport(models.Model):
	_name = 'accounting.balance.sheet.report'
	_inherit = ['portal.mixin','mail.thread', 'mail.activity.mixin']
	_description = 'Accounting Balance Sheet'

	@api.depends('from_date', 'to_date')
	def name_get(self):
		res = []
		for report in self:
			name = _('Báo cáo tình hình tài chính: %s - %s') % (report.from_date.strftime('%d/%m/%Y'), report.to_date.strftime('%d/%m/%Y'))
			res.append((report.id, name))
		return res

	def default_template_id(self):
		template_id = self.env['accounting.balance.template'].search([], order="id desc", limit=1)
		return template_id and template_id.id or False

	previous_id = fields.Many2one('accounting.balance.sheet.report','Previous period')
	from_date = fields.Date('From Date', required=True)
	to_date = fields.Date('To Date', required=True)
	template_id = fields.Many2one('accounting.balance.template','Template', default=default_template_id)
	line_ids = fields.One2many('accounting.balance.sheet.report.line','report_id')
	state = fields.Selection([
			('draft','Draft'),
			('closed','Closed'),
		],string="State", default='draft')
	company_id = fields.Many2one(comodel_name="res.company", string="Company", default=lambda self: self.env.company)

	@api.onchange('template_id')
	def onchange_template_id(self):
		for rec in self:
			template = rec.template_id
			if rec.line_ids:
				rec.line_ids.unlink()
			if rec.template_id and rec.template_id.balance_ids:
				rec.line_ids = [(0,0, {
						'balance_id': line and line.id or False,
						'code': line.code
					}) for line in rec.template_id.balance_ids]
			rec.template_id = template


	def action_calculate(self):
		business_cycle = self.env.company.business_cycle or 0

		def find_move_line(line,domain_add=[]):
			domain = [
				('date','>=', self.from_date),
				('date','<=', self.to_date),
				('account_id','in', line.balance_id.account_ids.ids),
				('parent_state', '=', 'posted'),
			] + domain_add	
			return self.env['account.move.line'].search(domain)

		def find_last_year_previous(line):
			if self.previous_id:
				lines = self.previous_id.line_ids.filtered(lambda x: x.code == line.code)
				return sum(lines.mapped('number_last_year')) if lines else 0
			return 0

		for line in self.line_ids.filtered(lambda x: x.balance_id and x.balance_id.apply_by != 'total_categ'):
			movelines = []
			number_last_year = 0
			number_first_year = find_last_year_previous(line) #lấy giá trị cuối năm của kỳ trước khớp  với dòng đang tính
			if line.balance_id.apply_by in ['total_debit_credit','total_credit_debit']:
				domain_add = []
				if line.balance_id.in_business_cycle:
					domain_add += ["|",('date_maturity', '=', False),('date_maturity', '<=', self.to_date + relativedelta(months=business_cycle))]
				else:
					domain_add += [
						'|',
						'&',('date_maturity','!=',False),('date_maturity', '>', self.to_date + relativedelta(months=business_cycle)),
						'&',('date_maturity','=',False),('date', '>', self.to_date + relativedelta(months=business_cycle))
					]
				movelines = find_move_line(line,domain_add=domain_add)
				debit = movelines and sum(movelines.mapped('debit')) or 0
				credit = movelines and sum(movelines.mapped('credit')) or 0
				#loại Tổng Nợ - Có theo tài khoản thì nợ trừ có, loại Tổng Có - Nợ theo tài khoản thì có - nợ
				number_last_year = debit - credit if line.balance_id.apply_by == 'total_debit_credit' else credit - debit

			if line.balance_id.apply_by in ['residual_value_debt','residual_value_credit']:
				#loại Lấy giá trị còn lại nợ trên phát sinh thì thêm đk tìm là credit trên bút toán = 0,
				#loại Lấy giá trị còn lại có trên phát sinh thì thêm đk tìm là debit trên bút toán = 0
				domain_add = [('credit', '=', 0)] if line.balance_id.apply_by == 'residual_value_debt' else [('debit', '=', 0)]
				if line.balance_id.in_business_cycle:
					domain_add += ["|",('date_maturity', '=', False),('date_maturity', '<=', self.to_date + relativedelta(months=business_cycle))]
				else:
					domain_add += [
						'|',
						'&',('date_maturity','!=',False),('date_maturity', '>', self.to_date + relativedelta(months=business_cycle)),
						'&',('date_maturity','=',False),('date', '>', self.to_date + relativedelta(months=business_cycle))
					]
				movelines = find_move_line(line,domain_add=domain_add)

				def check_to_calculate(move):
					amount_residual = abs(move.amount_residual) or 0
					for match in move.matched_debit_ids.filtered(lambda x: (x.debit_move_id.id == move.id or x.credit_move_id.id == move.id) \
						and (x.max_date < self.from_date or x.max_date > self.to_date)):
						amount_residual += match.debit_amount_currency

					for match in move.matched_credit_ids.filtered(lambda x: (x.debit_move_id.id == move.id or x.credit_move_id.id == move.id) \
						and (x.max_date < self.from_date or x.max_date > self.to_date)):
						amount_residual += match.debit_amount_currency

					return amount_residual

				for move in movelines:
					number_last_year += check_to_calculate(move)
				number_last_year = abs(number_last_year)

			number_last = number_last_year + number_first_year
			
			if line.balance_id.value_on_report == 'always_positive':
				number_last = abs(number_last)
			if line.balance_id.value_on_report == 'zero_when_negative':
				if number_last < 0:
					number_last = 0

			line.write({
				'number_first_year': number_first_year,
				'number_last_year': number_last,
				'move_line_ids': [(6,0, movelines and movelines.ids or [])]
			})

		for line in self.line_ids.filtered(lambda x: x.balance_id and x.balance_id.apply_by == 'total_categ').sorted(lambda x: x.balance_id.stt_calculate):
			line_ids = self.line_ids.filtered(lambda x: x.balance_id.id in line.balance_id.total_categ_ids.ids)
			number_first_year = find_last_year_previous(line) #lấy giá trị cuối năm của kỳ trước khớp  với dòng đang tính
			number_last_year = sum(line_ids.mapped('number_last_year')) if line_ids else 0

			line.write({
				'number_first_year':number_first_year,
				'number_last_year':number_last_year,
				'move_line_ids': [(6,0, line_ids and line_ids.move_line_ids.ids or [])]
			})

	def unlink(self):
		for res in self:
			if res.state == 'closed':
				raise ValidationError(_('You cannot delete data in closed state'))

		return super(AccountingBalanceSheetReport, self).unlink()

	def action_closed(self):
		self.write({
			'state': 'closed'
		})

	def action_open(self):
		self.write({
			'state': 'draft'
		})

	def action_view_detail(self):
		action = self.env["ir.actions.actions"]._for_xml_id("biz_accounting_balance_sheet.action_accounting_balance_sheet_report_line")
		action['domain'] = [('id','in', self.line_ids.ids)]
		return action

class AccountingBalanceSheetReportLine(models.Model):
	_name = 'accounting.balance.sheet.report.line'
	_description = 'Accounting Balance Sheet Line'

	report_id = fields.Many2one('accounting.balance.sheet.report')
	balance_id = fields.Many2one('accounting.balance.sheet','Assets')
	code = fields.Char('Code')
	number_first_year = fields.Float('Number first year')
	number_last_year = fields.Float('Number last year')
	move_line_ids = fields.Many2many('account.move.line',string="Account move line", readonly=True)
	apply_by = fields.Selection(related="balance_id.apply_by", readonly=True)

	@api.onchange('balance_id')
	def onchange_balance_id(self):
		if self.balance_id:
			self.code = self.balance_id.code

	def write(self, vals):
		context = self._context
		if not context.get('pass_log', False):
			for res in self:
				check = False
				msg = "<b>" + _("Assets: %s"  % res.balance_id.display_name ) + "</b><ul>"
				for key, val in vals.items():
					if key in ['report_id','move_line_ids','apply_by']:
						continue

					name = self.env['ir.model.fields'].get_field_string(self._name)[key]
					old_value = res[key]
					new_value = val
					if key == 'balance_id':
						old_value = res[key].display_name
						new_value = self.env['accounting.balance.sheet'].browse(val).display_name

					if new_value != old_value:
						check = True
						msg += "<li> %s: %s -> %s"  % (name, old_value, new_value)
				msg += "</ul>"
				if check and res.report_id:
					res.report_id.message_post(body=msg) 

		return super().write(vals)
	
	def view_move_line(self):
		return {
            'type': 'ir.actions.act_window',
            'name': _('Move line detail'),
            'res_model': 'account.move.line',
            'view_mode': 'tree',
            'domain': [('id','in', self.move_line_ids.ids)]
		}