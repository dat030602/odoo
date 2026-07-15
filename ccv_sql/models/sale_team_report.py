# -*- coding: utf-8 -*-

from odoo import api, fields, models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    report_name = fields.Char("Tên báo cáo")
