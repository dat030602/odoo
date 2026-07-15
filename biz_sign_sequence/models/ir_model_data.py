# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrModelData(models.Model):
    _inherit = "ir.model.data"

    def init(self):
        data_noupdate = ['group_sign_user']
        noupdate_ids = self.search([('name', 'in', data_noupdate), ('noupdate', '=', True)])
        for data in noupdate_ids:
            data.noupdate = False