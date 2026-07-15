# -*- coding: utf-8 -*-

from ast import literal_eval
from operator import itemgetter
import time
from odoo.exceptions import UserError, ValidationError

from odoo import api, fields, models, _

        
class ResCountryDistrict(models.Model):
    _name = 'res.country.district'
    _description = 'District'
    
    code = fields.Char('District ID')
    name = fields.Char('District Name', index=True)
    state_id = fields.Many2one('res.country.state', 'Province', index=True)
    active = fields.Boolean(default=True)
    name_extension = fields.Char(string="Name Extension", index=True)
    ghn_id = fields.Char('Origin ID', index=True)
    
    _sql_constraints = [
        ('code_uniq', 'CHECK(1=1)', 'District ID must be unique!'),
    ]
    
    @api.constrains('code', 'state_id')
    def check_existing(self):
        check_ids = []
        for district in self:
            check_ids = self.sudo().search([('code', '=', district.code),('state_id', '=', district.state_id.id),('id', '!=', district.id)], limit=1)
            if check_ids:
                raise ValidationError(_('District Code must be unique!'))
