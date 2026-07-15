# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.misc import get_lang

class AccountMove(models.Model):
	_inherit = 'account.move'

	note = fields.Text("Note")
	creator_id = fields.Many2one("res.users", 'Vote Creator')
	chief_id = fields.Many2one("res.users", 'Chief Accounting Officer')
	unit_head_id = fields.Many2one("res.users", 'Unit head')