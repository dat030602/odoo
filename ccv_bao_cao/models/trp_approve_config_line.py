# -*- coding: utf-8 -*-

from odoo import fields, models


class TrpApproveConfigLine(models.Model):
    _inherit = 'trp.approve.config.line'

    manager_type = fields.Selection(
        selection_add=[('factory_team_leader', 'Tổ trưởng NM')],
        ondelete={'factory_team_leader': 'set default'},
    )
