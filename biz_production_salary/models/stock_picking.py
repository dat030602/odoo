# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    department_ids = fields.Many2many('hr.department',string='Departments')
    employee_ids = fields.Many2many('hr.employee',string='Employees')



class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'   
    
    user_id = fields.Many2one('res.users', string='Responsible User')
    supervisor_id = fields.Many2one('res.users', string='Người giám sát')
    apply_unit_pirce_cal_output_worker = fields.Boolean('Apply unit price to calculate output for workers?')
    apply_unit_price_goods_sold = fields.Boolean('Apply unit price for goods sold?')
    apply_unit_price_goods_imported = fields.Boolean('Apply unit price for goods imported?')

    def check_raise_choose_config(self):
        check_raise = False
        if self.apply_unit_pirce_cal_output_worker:
            if self.apply_unit_price_goods_sold or self.apply_unit_price_goods_imported:
                check_raise = True
        if self.apply_unit_price_goods_sold:
            if self.apply_unit_pirce_cal_output_worker or self.apply_unit_price_goods_imported:
                check_raise = True
        if self.apply_unit_price_goods_imported:
            if self.apply_unit_pirce_cal_output_worker or self.apply_unit_price_goods_sold:
                check_raise = True
        if check_raise:
            raise ValidationError(_('Please select only one configuration in the salary information tab'))


    @api.model_create_multi
    def create(self,vals):
        res = super(StockPickingType,self).create(vals)
        for rec in res:
            rec.check_raise_choose_config()
        return res

    def write(self,vals):
        res = super(StockPickingType,self).write(vals)
        for rec in self:
            rec.check_raise_choose_config()
        return res