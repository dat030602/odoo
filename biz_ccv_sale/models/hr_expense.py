# -*- coding: utf-8 -*-

from odoo import models, fields, api
# from odoo.addons.hr_expense.models.hr_expense import HrExpense as ORIGIN_Expense

class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=False, required=True, tracking=True, states={'done': [('readonly', True)]})
    
    @api.constrains('expense_line_ids', 'employee_id')
    def _check_employee(self):
        return True


class HrExpense(models.Model):
    _inherit = "hr.expense"

    payment_mode = fields.Selection(default='company_account')

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=False, required=True, tracking=True, states={'done': [('readonly', True)]})
    partner_name = fields.Char( string="Recipient Name")
    partner_bank_id = fields.Many2one('res.partner.bank', string='Recipient Bank Account')
    payment_type = fields.Selection(string="Payment Type", selection=[('cash', 'Cash'), ('bank', 'Bank')])
    
    @api.constrains('expense_line_ids', 'employee_id')
    def _check_employee(self):
        return True
        
    

    
    
    



