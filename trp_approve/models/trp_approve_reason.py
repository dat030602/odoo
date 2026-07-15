# -*- coding: utf-8 -*-

from odoo import fields, models, api


class TrpApproveReason(models.Model):
    _name = 'trp.approve.reason'
    _description = 'Lý do'

    name = fields.Char('Name', size=256, required=True)
    active = fields.Boolean('Active', default=True)
    res_model = fields.Char("Res Model")

    _sql_constraints = [('res_model_name_unique', 'unique (res_model, name)', "Lý do phải là duy nhất !")]
