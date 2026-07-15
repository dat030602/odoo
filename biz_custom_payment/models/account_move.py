# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _default_ref(self):
        payment_type = self._context.get('default_payment_type')
        if payment_type == 'inbound':
            return 'Thu tiền bán hàng từ - TT đơn hàng'
        if payment_type == 'outbound':
            return 'Công ty CCV'
        return ''

    invoice_symbol = fields.Char('Invoice symbol')
    ref = fields.Char(string='Reference', copy=False, tracking=True,default=_default_ref)