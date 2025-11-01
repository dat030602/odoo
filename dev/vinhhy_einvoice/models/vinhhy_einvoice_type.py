# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError


class VinhHyEInvoiceType(models.Model):
    _name = 'vinhhy.einvoice.type'
    _description = 'Vinh Hy E-Invoice Type'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    description = fields.Char(string='Description')
