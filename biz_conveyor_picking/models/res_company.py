# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,  _

class ResCompany(models.Model):
	_inherit = 'res.company'

	conveyor_username = fields.Char("Conveyor username")
	conveyor_password = fields.Char("Conveyor username")
