# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import date

class WzSelectTimeReport(models.TransientModel):
    _name = 'wz.select.time.report'
    _description = 'Wizard Select Time Report' 

    date_from = fields.Date('Date From', default=date.today())
    date_to = fields.Date('Date To', default=date.today())
    warehouse_ids = fields.Many2many('stock.warehouse', string='Kho')
    creator_id = fields.Many2one('res.users', string='Creator')
    accountant_chief_id = fields.Many2one('res.users', string='Chief accountant')
    unit_head_id = fields.Many2one('res.users', string='Unit Head')
    
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError(_("The 'Date To' must be greater than or equal to 'Date From'."))
    