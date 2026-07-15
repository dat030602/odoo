from odoo import models, fields


class View(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[('org', 'Org Chart')], ondelete={'org': 'cascade'})
