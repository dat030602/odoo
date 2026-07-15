# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, tools, _, Command

class ResUsers(models.Model):
    _inherit = "res.users"

    update_passwd = fields.Boolean(copy=False)