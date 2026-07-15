# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class Invite(models.TransientModel):
    _inherit = 'mail.wizard.invite'
    _description = 'Invite wizard'

    partner_ids = fields.Many2many(domain=[])