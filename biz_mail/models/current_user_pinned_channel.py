from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class CurrentUserPinnedChannel(models.Model):
    _name = 'current.user.pinned.channel'
    _description = "Current User's Pinned Channel"

    is_pinned = fields.Boolean('Is Pinned?')
    sequence = fields.Integer(default=0, string='Sequence')
    channel_id = fields.Many2one('mail.channel')
    user_id = fields.Many2one('res.users')
