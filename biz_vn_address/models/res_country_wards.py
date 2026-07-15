# -*- coding: utf-8 -*-

from ast import literal_eval
from operator import itemgetter
import time

from odoo import api, fields, models, _

class ResCountryWards(models.Model):
    _name = 'res.country.wards'
    _description = 'Wards'
    
    code = fields.Char('Wards ID')
    name = fields.Char('Wards Name', index=True)
    district_id = fields.Many2one('res.country.district', 'District', index=True)
    state_id = fields.Many2one('res.country.state', 'Province', index=True)
    active = fields.Boolean(default=True)
    name_extension = fields.Char(string="Name Extension", index=True)
    ghn_id = fields.Char('Origin ID', index=True)
    
    def check_existing(self, Code, DistrictID, ProvinceID):
        check_ids = self.search([('code', '=', Code),('district_id', '=', DistrictID),('state_id', '=' , ProvinceID)], limit=1)
        return check_ids and True or False
    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override search() to always show inactive children when searching via ``child_of`` operator. The ORM will
        always call search() with a simple domain of the form [('parent_id', 'in', [ids])]. """
        # a special ``domain`` is set on the ``child_ids`` o2m to bypass this logic, as it uses similar domain expressions
        if len(args) == 1 and len(args[0]) == 3 and args[0][:2] == ('parent_id','in') \
                and args[0][2] != [False]:
            self = self.with_context(active_test=False)
        return super(ResCountryWards, self)._search(args, offset=offset, limit=limit, order=order,
                                            count=count, access_rights_uid=access_rights_uid)
