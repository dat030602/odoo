# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

from vietnam_number import n2w


class AlphaInternalAccount(models.Model):
    _inherit = 'alpha.internal.account'

    partner_bank_id = fields.Many2one('res.partner.bank', string="Tài khoản ngân hàng")
    partner_name = fields.Char(string="Người thụ hưởng")
    partner_id = fields.Many2one("res.partner", string="Đối tượng", related="user_id.partner_id", store=True)
    type = fields.Selection([('transfer', 'Chuyển khoản'), ('cash', 'Tiền mặt')], string="Hình thức thanh toán", default="transfer")

    @api.onchange('type')
    def onchange_type(self):
        if self.type == 'cash':
            self.partner_bank_id = False

    def convert_money(self, value):
        value = int(value)
        result = n2w(str(int(value))).capitalize() + self.company_currency_id.name
        if result.find("không trăm nghìn không trăm" + self.company_currency_id.name) > -1:
            result = result.replace("không trăm nghìn không trăm" + self.company_currency_id.name, '')
        elif result.find("không trăm" + self.company_currency_id.name) > -1:
            result = result.replace("không trăm" + self.company_currency_id.name, '')
        else:
            result = n2w(str(int(value))).capitalize() + ' '
        return result

    def convert_vnd(self, amount):
        a = format(amount, ',.0f')
        return a.replace(',', '.')

    def convert_today(self):
        today = date.today()
        return "Ngày %s tháng %s năm %s" % (today.day, today.month, today.year)

    def convert_print(self, value):
        if not value:
            return ''
        if str(value).find('202') > -1:
            return str(value).split('-')[2] + '/' + str(value).split('-')[1] + '/' + str(value).split('-')[0]
