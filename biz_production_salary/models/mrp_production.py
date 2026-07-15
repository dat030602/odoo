# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    department_ids = fields.Many2many('hr.department',string='Departments',compute="_compute_department_ids",store=True,readonly=False)
    employee_ids = fields.Many2many('hr.employee',string='Employees')

    @api.depends('warehouse_id')
    def _compute_department_ids(self):
        for res in self:
            res.department_ids = res.warehouse_id.department_ids if res.warehouse_id else False
            
    @api.onchange('picking_type_id')
    def load_user_id(self):
        for res in self:
            user_id = False
            if res.picking_type_id.user_id:
                user_id = res.picking_type_id.user_id
            res.user_id = user_id