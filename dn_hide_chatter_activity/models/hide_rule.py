from odoo import models, fields

class HideChatterActivityRule(models.Model):
    _name = 'dn.hide.chatter.activity.rule'
    _description = 'Hide Chatter and Activity Rule'

    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', store=True)
    hide_chatter = fields.Boolean(string='Hide Chatter', default=False)
    hide_activity = fields.Boolean(string='Hide Activity', default=False)

    _sql_constraints = [
        ('model_uniq', 'unique(model_id)', 'Only one rule per model is allowed!')
    ]
