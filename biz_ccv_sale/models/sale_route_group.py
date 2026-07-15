# -*- coding: utf-8 -*-
# Part

from odoo import models, fields, api, _

class SaleRouteGroup(models.Model):
	_name = 'sale.route.group'
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_description = 'Sale Route Group'

	name = fields.Char('Name', translate=True)
	code = fields.Char('Code group')
	company_id= fields.Many2one('res.company')
	active = fields.Boolean(default=True)