# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MisaInbotRelatedLine(models.Model):
    _name = 'misa.inbot.related.line'
    _description = 'MISA INBOT Related Invoices (InfoND123)'
    _order = 'id asc'

    document_id = fields.Many2one(
        'misa.inbot.document',
        string='INBOT Document',
        required=True,
        ondelete='cascade',
        index=True
    )
    rel_template_no = fields.Char(string='Related Template No')
    rel_series = fields.Char(string='Related Series')
    rel_invoice_no = fields.Char(string='Related Invoice No')
    rel_invoice_date = fields.Date(string='Related Invoice Date')
    related_type = fields.Selection([
        ('1', 'Thay thế (Replacement)'),
        ('2', 'Điều chỉnh (Adjustment)'),
        ('3', 'Khác (Other)'),
    ], string='Related Type', default='1')

    original_inbot_id = fields.Many2one(
        'misa.inbot.document',
        string='Original INBOT Document',
        help='Linked original INBOT document record in the system if matched'
    )
