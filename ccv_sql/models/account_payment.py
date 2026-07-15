# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from .component import vietnam_number
# from vietnam_number import n2w


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_slip_creator_id = fields.Many2one(
        'res.users', string="Người lập phiếu",
        help="Người lập phiếu hiển thị trên bản in phiếu chi/phiếu thu. "
             "Nếu để trống sẽ lấy theo người tạo phiếu.")

    def action_print_giay_bao_co(self):
        if not self.get_account_payment():
            raise ValidationError("Chưa có khoản tiền thanh toán")
        if self.payment_type == 'inbound':
            return self.env.ref('ccv_sql.giay_bao_co_report').report_action(self)
        if self.payment_type == 'outbound':
            return self.env.ref('ccv_sql.giay_bao_no_report').report_action(self)

    def get_account_payment(self):
        if self.payment_type == 'inbound':
            move_line_ids = self.invoice_line_ids.filtered(lambda x: x.debit > 0)
            if len(move_line_ids) > 0:
                return move_line_ids[0]
        if self.payment_type == 'outbound':
            move_line_ids = self.invoice_line_ids.filtered(lambda x: x.credit > 0)
            if len(move_line_ids) > 0:
                return move_line_ids[0]
        return False

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
