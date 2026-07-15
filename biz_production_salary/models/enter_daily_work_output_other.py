# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class EnterDailyWorkOutputOther(models.Model):
    _name = 'enter.daily.work.output.other'
    _description = 'Enter daily work output/other'

    date = fields.Date('Date')
    product_id = fields.Many2one('product.product','Product Name')
    production_other = fields.Float('Production, other')
    employee_ids = fields.Many2many('hr.employee',string='Employees')
    department_ids = fields.Many2many('hr.department',string='Departments')
    price_unit = fields.Float('Price Unit')
    day_labor_id = fields.Many2one('day.labor',string='Day Labor Coefficient')

    @api.onchange('product_id')
    def onchange_product_id(self):
        for res in self:
            res.price_unit = res.product_id.unit_price_cal_out_worker

    @api.onchange('day_labor_id')
    def onchange_day_labor_id(self):
        for res in self:
            res.price_unit = res.day_labor_id.unit_price