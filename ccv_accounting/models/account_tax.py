from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime
import logging
import math
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    @api.model
    def _compute_taxes_for_single_line(self, base_line, handle_price_include=True, include_caba_tags=False, early_pay_discount_computation=None, early_pay_discount_percentage=None):
        tax_amount_value = 0
        if base_line:
            record = base_line['record']
            extra_context = base_line['extra_context'] if base_line['extra_context'] is not None else {}
            if record and record._name == 'account.move.line':
                tax_amount_value = record.tax_amount_value
                extra_context.update({'tax_amount_value':tax_amount_value})
                base_line['extra_context'] = extra_context
        res = super(AccountTax,self.with_context(fixed_tax_amount=tax_amount_value))._compute_taxes_for_single_line(base_line, handle_price_include, include_caba_tags, early_pay_discount_computation, early_pay_discount_percentage)
        
        # Sửa lỗi Odoo tính toán sai dấu thuế cho dòng chiết khấu (giá trị âm)
        if tax_amount_value and res and 'taxes' in res:
            for tax_data in res['taxes']:
                amount_key = 'tax_amount' if 'tax_amount' in tax_data else ('amount' if 'amount' in tax_data else None)
                if amount_key and tax_amount_value < 0 and tax_data[amount_key] > 0:
                    tax_data[amount_key] = -tax_data[amount_key]
                elif amount_key and tax_amount_value > 0 and tax_data[amount_key] < 0:
                    tax_data[amount_key] = abs(tax_data[amount_key])
                    
        return res


    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True, include_caba_tags=False, fixed_multiplicator=1):
        res = super(AccountTax, self).compute_all(price_unit, currency, quantity, product, partner, is_refund, handle_price_include, include_caba_tags, fixed_multiplicator)
        
        # Đảm bảo tiền thuế luôn cùng dấu với thành tiền (fix lỗi Odoo tính thuế dương cho dòng chiết khấu)
        if price_unit * quantity < 0 and res and 'taxes' in res:
            for tax_data in res['taxes']:
                if tax_data.get('amount', 0) > 0:
                    tax_data['amount'] = -tax_data['amount']
                    
        return res

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None, fixed_multiplicator=1):
        # _logger.info(self.env.context)
        fixed_tax_amount = self.env.context.get('tax_amount_value',0)
        if not fixed_tax_amount:
            res = super(AccountTax,self)._compute_amount(base_amount, price_unit, quantity, product, partner, fixed_multiplicator)
        else:
            res = fixed_tax_amount
        return res