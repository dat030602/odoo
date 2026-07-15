from odoo import fields, models, api

class ResUsers(models.Model):
	_inherit = 'res.users'

	pdf_password = fields.Char("PDF Password")
