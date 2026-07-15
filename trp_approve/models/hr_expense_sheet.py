# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo import fields, Command
from vietnam_number import n2w


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    internal_account_id = fields.Many2one("alpha.internal.account", string="Đề nghị tạm ứng")
    internal_account_ids = fields.Many2many("alpha.internal.account", string="Đề nghị tạm ứng")
    count_payment = fields.Integer('Count Payment', compute="compute_count_payment")
    
    def compute_count_payment(self):
        for res in self:
            count_payment = 0
            payments = self.env['account.payment'].search([('expense_sheet_origin', '=', res.id)])
            if payments:
                count_payment = len(payments)
            res.count_payment = count_payment

    def convert_vnd(self, amount):
        a = format(amount, ',.0f')
        return a.replace(',', '.')

    def convert_print(self, value):
        if not value:
            return ''
        if str(value).find('202') > -1:
            return str(value).split('-')[2] + '/' + str(value).split('-')[1] + '/' + str(value).split('-')[0]

        return value

    def action_create_payment(self):   
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'context': {
            	'default_internal_account_id': self.internal_account_id.id,
            	'default_expense_sheet_origin': self.id,
            },
            'target': 'current'
        }    
    
    def action_open_payment(self):
        payments = self.env['account.payment'].search([('expense_sheet_origin', '=', self.id)])
        return {
            'name': _('Thanh toán'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'account.payment',
            'domain': [('id', 'in', payments.ids)]
        }