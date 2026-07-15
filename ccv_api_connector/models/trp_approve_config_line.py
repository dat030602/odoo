# -*- coding: utf-8 -*-

from odoo import fields, models


class TrpApproveConfigLine(models.Model):
    _inherit = 'trp.approve.config.line'

    manager_type = fields.Selection(
        selection_add=[('loading', 'Bốc xếp')],
        ondelete={'loading': 'set default'},
    )
