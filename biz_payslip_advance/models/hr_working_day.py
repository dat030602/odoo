# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class hr_type_working_day(models.Model):
    _name = 'hr.type.working.day'
    _description = 'Working Day Type'
    
    name = fields.Char('Type Name')
    code = fields.Char('Type Code')
    type_value = fields.Selection([('day','Day'),('hours','Hours')], string='Type Value', default='day')
    column_import = fields.Many2one('hr.type.working.day.import', string='Row number of import file')
    
    @api.model_create_multi
    def create(self, vals):
        res = super(hr_type_working_day, self).create(vals)
        for working_obj in res:
            if working_obj.column_import:
                working_obj.column_import.write({'working_id': working_obj.id})
        return res
    
    
    def write(self,vals):
        for record in self:
            if 'column_import' in vals:
                column_import = vals.get('column_import',False)
                if record.column_import:
                    column_obj = self.env['hr.type.working.day.import'].browse(record.column_import.id)
                    column_obj.write({'working_id':False})
                if column_import:
                    column_obj = self.env['hr.type.working.day.import'].browse(column_import)
                    column_obj.write({'working_id': record.id})
        return super(hr_type_working_day, self).write(vals)
    
    
    def unlink(self):
        for record in self:
            if record.column_import:
                column_obj = self.env['hr.type.working.day.import'].browse(record.column_import.id)
                column_obj.write({'working_id':False})
        return super(hr_type_working_day, self).unlink()
    
class hr_type_working_day_import(models.Model):
    _name = 'hr.type.working.day.import'
    _description = 'Column Working Day Import'
    
    name = fields.Char('Name')
    working_id = fields.Many2one('hr.type.working.day', string='Working Day Type', default=False)
    