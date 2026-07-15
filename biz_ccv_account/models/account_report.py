from odoo import models, fields, api, _, osv, _lt

class AccountReport(models.Model):
    _inherit = 'account.report'

    digits = fields.Integer('Digits')

    def format_value(self, value, currency=False, blank_if_zero=True, figure_type=None, digits=1):
        if self.digits:
            digits = self.digits

        return super(AccountReport, self).format_value(value, currency, blank_if_zero, figure_type, digits)