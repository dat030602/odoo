# -*- coding: utf-8 -*-
from odoo import models, fields


class TrpApproveConfigLine(models.Model):
    _inherit = 'trp.approve.config.line'

    manager_type = fields.Selection(selection_add=[
        ('creator', 'Người LB'),
        ('commercial_department', 'Phòng TM'),
        ('team_sale', 'Trưởng KV'),
    ])
