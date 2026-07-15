# -*- coding: utf-8 -*-
from odoo import fields, models

class TrpApproveHistory(models.Model):
    _inherit = 'trp.approve.history'

    dsk_customer_id = fields.Many2one('details.sales.book.by.customer', string='Sổ chi tiết bán hàng theo khách hàng')
