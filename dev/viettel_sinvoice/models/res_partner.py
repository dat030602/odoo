# -*- coding: utf-8 -*-

from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    budget_code = fields.Char('Budget Code', help='Mã ngân sách nhà nước', tracking=True)
    identification_no = fields.Char('Identification Number', help='CCCD', tracking=True)
