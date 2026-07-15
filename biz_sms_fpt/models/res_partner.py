# -*- coding: utf-8 -*-

from odoo import fields, models


class Contact(models.Model):
    _inherit = "res.partner"

    fpt_date_of_birth = fields.Date(string="Birthday", copy=False)