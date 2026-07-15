# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TrpApproveConfigLineDetail(models.Model):
    _inherit = 'trp.approve.config.line'

    approver_field = fields.Char(string="Approver Field")
