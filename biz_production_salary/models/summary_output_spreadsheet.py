# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class SummaryOfOutputSpreadsheet(models.Model):
	_name = 'summary.output.spreadsheet'
	_description = 'Summary of output spreadsheet'
	_order = 'summary_id,date,picking_type_id'

	summary_id = fields.Many2one('summary.output.daily.work', ondelete='cascade')
	date = fields.Date('Date')
	product_id = fields.Many2one('product.product','Product Name')
	picking_type_id = fields.Many2one('stock.picking.type',string="Type of activity")
	output_pro = fields.Float('Output',digits="Product Unit of Measure")
	input_pro = fields.Float('Input',digits="Product Unit of Measure")
	other_output = fields.Float('Other Output',digits="Product Unit of Measure")
	day_labor = fields.Float('Day Labor',digits="Product Unit of Measure")
	production = fields.Float('Production',digits="Product Unit of Measure")
	total_quantity = fields.Float('Total Quantity',compute="_compute_total_quantity",store=True,digits="Product Unit of Measure")
	price_unit = fields.Monetary('Price Unit')
	total_amount = fields.Monetary('Total amount',compute="_compute_total_amount",store=True)
	total_amount_1_person = fields.Monetary('Total Amount/1 person',compute="_compute_total_amount_1_person",store=True)

	employee_enjoys_ids = fields.One2many('employee.enjoys','summary_line_id',string="Employee Enjoys")
	output_move_ids = fields.Many2many('stock.move','stock_output_move_rel','output_id','stock_output_id',string="Output Moves")
	intput_move_ids = fields.Many2many('stock.move','stock_input_move_rel','input_id','stock_input_id',string="Input Moves")
	production_move_ids = fields.Many2many('stock.move','stock_production_move_rel','production_id','stock_production_id',string="Production Moves")
	currency_id = fields.Many2one(related='summary_id.currency_id',string="Currency")


	@api.depends('output_pro','input_pro','other_output','production')
	def _compute_total_quantity(self):
		for res in self:
			res.total_quantity = res.output_pro + res.input_pro + res.other_output + res.production + res.day_labor

	@api.depends('total_quantity','price_unit')
	def _compute_total_amount(self):
		for res in self:
			res.total_amount = res.total_quantity * res.price_unit

	@api.depends('total_amount','employee_enjoys_ids.rate')
	def _compute_total_amount_1_person(self):
		for res in self:
			total_rate = sum(res.employee_enjoys_ids.mapped('rate'))
			if total_rate > 0:
				res.total_amount_1_person = res.total_amount / total_rate
			else:
				res.total_amount_1_person = 0.0

	def action_open_output_move(self):
		action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
		if len(self.output_move_ids.picking_id.ids) == 1:
			action['view_mode'] = 'form'
			action['views'] = [(False, 'form')]
			action['res_id'] = self.output_move_ids.picking_id.id
		else:
			action['domain'] = [('id', 'in', self.output_move_ids.picking_id.ids)]
		return action

	def action_open_input_move(self):
		action = self.env.ref('stock.action_picking_tree_all').sudo().read()[0]
		if len(self.intput_move_ids.picking_id) == 1:
			action['view_mode'] = 'form'
			action['views'] = [(False, 'form')]
			action['res_id'] = self.intput_move_ids.picking_id.id
		else:
			action['domain'] = [('id', 'in', self.intput_move_ids.picking_id.ids)]
		return action

	def action_open_production(self):
		action = self.env.ref('mrp.mrp_production_action').sudo().read()[0]
		if len(self.production_move_ids.production_id) == 1:
			action['view_mode'] = 'form'
			action['views'] = [(False, 'form')]
			action['res_id'] = self.production_move_ids.production_id.id
			action['context'] = {'default_id': self.production_move_ids.production_id.id}
		else:
			action['domain'] = [('id', 'in', self.production_move_ids.production_id.ids)]
		return action

	def action_open_employee_enjoys(self):
		action = self.env.ref('biz_production_salary.action_employee_enjoys').sudo().read()[0]
		action['domain'] = [('id', 'in', self.employee_enjoys_ids.ids)]
		return action

