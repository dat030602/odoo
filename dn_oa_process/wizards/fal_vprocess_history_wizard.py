# -*- coding: utf-8 -*-
from odoo import fields, models


class FalVprocessHistoryWizard(models.TransientModel):
    _name = "fal.vprocess.history.wizard"
    _description = "Approval History Wizard"

    res_model = fields.Char(required=True, readonly=True)
    res_id = fields.Integer(required=True, readonly=True)
    history_html = fields.Html(readonly=True, sanitize=False)
