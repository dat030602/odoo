#-*- coding: utf-8 -*-

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _cron_update_ocn_token(self):
        try:
            records = self.search([("ocn_token", "!=", False)])
            for rec in records:
                rec.update({"ocn_token": False})
        except Exception as error:
            print("error", error)

