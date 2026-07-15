# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models,  _

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	conveyor_username = fields.Char("Conveyor username", related='company_id.conveyor_username', readonly=False)
	conveyor_password = fields.Char("Conveyor username", related='company_id.conveyor_password', readonly=False)
