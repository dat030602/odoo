# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ConfigTeleSale(models.Model):
	_inherit = 'kpi.scorecard.line'

	kpi_config_id = fields.Many2one('config.telesale', string='KPI Config', compute='_compute_kpi_config_id', store=True)

	@api.depends('kpi_id')
	def _compute_kpi_config_id(self):
		for res in self:
			if res.kpi_id:
				kpi_config_id = self.env['config.telesale'].search([('kpi_item_ids', 'in', res.kpi_id.ids)], limit=1)
				res.kpi_config_id = kpi_config_id
			else:
				res.kpi_config_id = False
				
	def _action_create_kpi_config(self):
		for rec in self:
			if not rec.kpi_config_id:
				rec.env['config.telesale'].sudo().create({
					'target': rec.kpi_id.name,
					'code': 'LKPIDSHH',
					'how_to_calculate': 'config_telesale' if not rec.employee_id.is_manager_sales else 'kpi_workload',
					'calculate_kpis_by': 'by_output' if not rec.employee_id.is_manager_sales else False,
					'calculate_the_amount_earned': 'config_telesale' if not rec.employee_id.is_manager_sales else False,
					'kpi_item_ids': [(6, 0, rec.kpi_id.ids)],
					'employee_ids': [(6, 0, rec.employee_id.ids)],
					'configure_related_output_kpis': rec.kpi_id.id if rec.employee_id.is_manager_sales else False,
				})
	
	def action_open_kpi_config(self):
		if not self.kpi_config_id:
			self._action_create_kpi_config()
		if self.kpi_config_id.line_ids.exists():
			action = self.env.ref('biz_business_salary.action_config_telesale_line').sudo().read()[0]
			action['domain'] = [('config_id', '=', self.kpi_config_id.id)]
			action['context'] = {'default_config_id': self.kpi_config_id.id}
		else:
			action = self.env.ref('biz_business_salary.action_config_telesale').sudo().read()[0]
			action['view_mode'] = 'form'
			action['views'] = [(False, 'form')]
			action['res_id'] = self.kpi_config_id.id
		return action
	