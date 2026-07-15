# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, Command, _


class SignItemParty(models.Model):
    _inherit = "sign.item.role"

    change_authorized = fields.Boolean(default=True)

