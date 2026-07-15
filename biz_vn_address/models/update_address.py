# -*- coding: utf-8 -*-
from odoo import fields, api, models,_

class UpdateCountryState(models.Model):
	_name = 'update.country.state'
	_description = "Update Province"

	name = fields.Char('Name')
	state_id = fields.Many2one('res.country.state')
	country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',default=lambda self: self.env.ref('base.vn').id)
	is_updated = fields.Boolean('Updated')
	delivery_type = fields.Selection([])

	def action_update(self):
		return True

class UpdateCountryDistrict(models.Model):
	_name = 'update.country.district'
	_description = "Update District"

	name = fields.Char('Name')
	district_id = fields.Many2one('res.country.district','District')
	state_id = fields.Many2one('res.country.state','Province')
	country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',default=lambda self: self.env.ref('base.vn').id)
	is_updated = fields.Boolean('Updated')
	delivery_type = fields.Selection([])

	def action_update(self):
		return True

class UpdateCountryWards(models.Model):
	_name = 'update.country.wards'
	_description = "Update Ward"

	name = fields.Char('Name')
	wards_id = fields.Many2one('res.country.wards','Wards')
	district_id = fields.Many2one('res.country.district','District')
	state_id = fields.Many2one('res.country.state','Province')
	country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',default=lambda self: self.env.ref('base.vn').id)
	is_updated = fields.Boolean('Updated')
	delivery_type = fields.Selection([])

	def action_update(self):
		return True
