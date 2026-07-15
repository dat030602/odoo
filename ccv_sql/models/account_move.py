# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from .component import vietnam_number

import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.move'

    internal_account_id = fields.Many2one("alpha.internal.account")

    def action_get_data_report(self):
        # bản in phiếu thu
        partner_id = self.partner_id
        debit_code = self.line_ids.filtered(lambda x: x.debit > 0).mapped('account_id').mapped('code')
        credit_code = self.line_ids.filtered(lambda x: x.credit > 0).mapped('account_id').mapped('code')
        employee_id = self.env['hr.employee'].search([('user_id.partner_id', '=', partner_id.id)])
        if employee_id and employee_id.department_id:
            departner_name = employee_id.department_id.name
        else:
            departner_name = partner_id.contact_address_complete
        data = []
        data.append({
            'debit_code':  ','.join(list(set(debit_code))) if debit_code else '',
            'credit_code':  ','.join(list(set(credit_code))) if credit_code else '',
            'partner_name': partner_id.name,
            'departner_name': departner_name,
            'ref': self.ref,
            'amount': sum(self.line_ids.filtered(lambda x: x.credit > 0).mapped('credit')),
        })
        return data

    def action_get_data_report_phieu_chi(self):
        # bản in phiếu chi
        partner_ids = self.line_ids.filtered(lambda x: x.credit > 0).mapped('partner_id')
        account_dest_id = self.line_ids.filtered(lambda x: x.debit > 0)[0].account_id
        data = []
        for partner_id in partner_ids:
            employee_id = self.env['hr.employee'].search([('user_id.partner_id', '=', partner_id.id)])
            if employee_id and employee_id.department_id:
                departner_name = employee_id.department_id.name
            else:
                departner_name = partner_id.contact_address_complete
            account_ids = set(self.line_ids.filtered(lambda x: x.credit > 0 and x.partner_id == partner_id).mapped('account_id'))
            debit_code = []
            ref = []
            amount = 0
            for account_id in account_ids:
                line_ids = self.line_ids.filtered(lambda x: x.credit > 0 and x.partner_id == partner_id
                                                         and x.account_id == account_id)
                ref.append(line_ids[0].name or '')
                amount = sum(line_ids.mapped('credit'))
                debit_code.append(account_id.code)
            data.append({
                'debit_code':  ', '.join(list(set(debit_code))),
                'credit_code':  account_dest_id.code,
                'partner_name': partner_id.name,
                'departner_name': departner_name,
                'ref': '; '.join(list(set(ref))),
                'amount': amount,
            })
        return data

    def convert_vnd(self, amount):
        a = format(amount, ',.0f')
        return a.replace(',', '.')

    def convert_usd(self, amount):
        a = format(amount, ',.2f')
        return a

    def convert_date(self, date):
        today = date
        return "Ngày %s tháng %s năm %s" % (today.day, today.month, today.year)

    def convert_print(self, value):
        if not value:
            return ''
        if str(value).find('202') > -1:
            return str(value).split('-')[2] + '/' + str(value).split('-')[1] + '/' + str(value).split('-')[0]

        return value

    def convert_money(self, value):
        return vietnam_number(int(value)).capitalize() + ' đồng'

