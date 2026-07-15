# -*- coding: utf-8 -*-
from odoo import models, fields

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    is_unc_sender = fields.Boolean(string='Tài khoản gửi UNC', default=False)
