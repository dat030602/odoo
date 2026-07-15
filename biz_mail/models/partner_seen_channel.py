from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class PartnerSeenChannel(models.Model):
    _name = 'partner.seen.channel'
    _description = 'Partner Seen Channel'

    partner_id = fields.Many2one('res.partner')
    seen_time = fields.Datetime()
    channel_id = fields.Many2one('mail.channel')