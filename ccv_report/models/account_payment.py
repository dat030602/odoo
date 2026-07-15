# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from vietnam_number import n2w


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_print_giay_bao_co(self):
        if not self.get_account_payment():
            raise ValidationError("Chưa có khoản tiền thanh toán")
        if self.payment_type == 'inbound':
            return self.env.ref('ccv_report.giay_bao_co_report_ccv_report').report_action(self)
        if self.payment_type == 'outbound':
            return self.env.ref('ccv_report.giay_bao_no_report_ccv_report').report_action(self)
