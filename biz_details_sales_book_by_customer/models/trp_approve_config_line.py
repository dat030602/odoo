# -*- coding: utf-8 -*-

from odoo import models, fields


class TrpApproveConfigLine(models.Model):
    _inherit = 'trp.approve.config.line'

    manager_type = fields.Selection(selection_add=[
        ('creator', 'NLB'),
        ('statistics', 'TK BĐH'),
        ('account_liability', 'Phòng KT'),
        ('accountant_chief', 'Kế toán T'),
        ('unit_head', 'TTDV'),
    ])
