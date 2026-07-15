from odoo import models, fields, api, _
from odoo.tools import float_compare, float_is_zero


class CheckExchangeRateWizard(models.TransientModel):
    _name = 'check.exchange.rate.wizard'
    _description = 'Check Exchange Rate Wizard'

    move_id = fields.Many2one(
        'account.move', string='Bill', required=True)
    currency_id = fields.Many2one(
        'res.currency', related='move_id.currency_id')
    purchase_ids = fields.Many2many('purchase.order')
    line_ids = fields.One2many(
        'check.exchange.rate.wizard.line', 'wizard_id', string='Lines')

    @api.onchange('purchase_ids')
    def _onchange_purchase_ids(self):
        move = self.move_id
        origin_exchange_rate = move.inverse_manural_currency_exchange_rate
        lines = [(5, 0, 0), (0, 0, {
            'name': move.name,
            'exchange_rate': origin_exchange_rate,
            'diff_exchange_rate': _('Origin')
        })]
        if self.purchase_ids:
            precision_digit = move.currency_id.decimal_places
            format_diff = '%.' + str(precision_digit) + 'f'
            for order in self.purchase_ids:
                purchase_exchange_rate = order.inverse_manural_currency_exchange_rate
                diff_exchange_rate = purchase_exchange_rate - origin_exchange_rate
                compare_result = float_compare(
                    diff_exchange_rate, 0.0, precision_digits=precision_digit)
                if compare_result == 0:
                    diff = format_diff % 0
                elif compare_result > 0:
                    diff = '+' + str(format_diff % diff_exchange_rate)
                else:
                    diff = str(format_diff % diff_exchange_rate)
                lines.append((0, 0, {
                    'name': order.name,
                    'exchange_rate': purchase_exchange_rate,
                    'diff_exchange_rate': diff
                }))
        self.line_ids = lines


class CheckExchangeRateWizardLine(models.TransientModel):
    _name = 'check.exchange.rate.wizard.line'
    _description = 'Check Exchange Rate Wizard Line'

    name = fields.Char(required=True)
    exchange_rate = fields.Float(digits=(12, 2))
    diff_exchange_rate = fields.Char()
    wizard_id = fields.Many2one('check.exchange.rate.wizard', required=True)
