from odoo import api, fields, models, tools, _

class ResUsers(models.Model):
	_inherit = 'res.users'

	name_without_position = fields.Char("Name without position")