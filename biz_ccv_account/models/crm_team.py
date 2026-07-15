from odoo import api, fields, models,_
from odoo.osv import expression


class CrmTeam(models.Model):
	_inherit = 'crm.team'

	sales_assistant_ids = fields.Many2many('res.users','res_team_assistant_ids','team_id','assisng_id','Sales Assistant')