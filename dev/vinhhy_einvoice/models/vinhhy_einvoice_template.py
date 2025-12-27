# -*- coding: utf-8 -*-
import json

import requests

from odoo import models, fields, api
from odoo.exceptions import UserError


class VHEInvoiceTemplate(models.Model):
    _name = 'vinhhy.einvoice.template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Vinh Hy E-Invoice Template'
    _rec_name = 'name'

    name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    vat = fields.Char()
    type_id = fields.Many2one('vinhhy.einvoice.type', 'Invoice Type', tracking=True, required=True)
    invoice_type_code = fields.Char(related='type_id.code', store=True, string='Invoice Type Code')
    template_code = fields.Char('Template Code', tracking=True, required=True)  # Mẫu hoá đơn
    series = fields.Char('Series', tracking=True, copy=False)  # Ký hiệu hoá đơn
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('branch_template_series_uniq', 'unique (branch_id, template_code, series)',
         'The combination of Branch, Template and Series must be unique!'),
    ]

    @api.depends('invoice_type_code', 'template_code', 'series')
    def _compute_display_name(self):
        names = dict(self.name_get())
        for tmpl in self:
            tmpl.name = names.get(tmpl.id)

    @api.depends('invoice_type_code', 'template_code', 'series')
    def _compute_display_name(self):
        for record in self:
            name_display = "%s / %s" % (record.invoice_type_code, record.series)
            record.name = name_display