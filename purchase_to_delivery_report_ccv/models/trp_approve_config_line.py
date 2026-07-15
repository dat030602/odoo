# -*- coding: utf-8 -*-
from odoo import fields, models

class TrpApproveConfigLine(models.Model):
    _inherit = 'trp.approve.config.line'

    manager_type = fields.Selection(
        selection_add=[('factory', 'Nhà máy')],
        ondelete={'factory': 'set default'},
    )
