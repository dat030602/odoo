# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import requests
from odoo.exceptions import UserError, AccessError
import json
from datetime import datetime, timedelta

class SinvoiceCancel(models.Model):
    _name = "sinvoice.cancel"
    _description = "Sinvoice cancel"

    additionalReferenceDate = fields.Datetime(required=True)
    reason = fields.Char(required=True)
    additionalReferenceDesc = fields.Char('Additional Reference Desc',required=True)

    def do_cancel(self):
        active_model = self._context.get('active_model')
        active_model_id = self.env[active_model].browse(self._context.get('active_id'))
        if active_model_id:
            data_cancel = {
                "reason": self.reason,
                "additionalReferenceDesc": self.additionalReferenceDesc,
                "additionalReferenceDate": '%s' % (int(self.additionalReferenceDate.timestamp()) * 1000),
            }
            active_model_id.action_cancel_sinvoice(data_cancel)
        return {
            "name": "Viettel Sinvoice",
            "type": "ir.actions.act_window",
            "res_model": active_model,
            "res_id": active_model_id.id,
            "views": [(False, "form")],
        }