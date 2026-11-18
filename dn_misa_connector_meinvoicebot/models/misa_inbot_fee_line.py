# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MisaInbotFeeLine(models.Model):
    _name = 'misa.inbot.fee.line'
    _description = 'MISA INBOT Fee Line'
    _order = 'id asc'

    document_id = fields.Many2one(
        'misa.inbot.document',
        string='INBOT Document',
        required=True,
        ondelete='cascade',
        index=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='document_id.currency_id',
        store=True
    )
    fee_name = fields.Char(string='Fee Name', required=True)
    fee_amount = fields.Monetary(string='Fee Amount', currency_field='currency_id')
