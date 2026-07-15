from odoo import models, fields, api
import logging
from datetime import datetime
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.model
    def convert_money(self, amount, currency_id=False):
        units = ['', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín']
        tens = ['', 'mười', 'hai mươi', 'ba mươi', 'bốn mươi', 'năm mươi', 'sáu mươi', 'bảy mươi', 'tám mươi', 'chín mươi']
        thousands = ['', 'nghìn', 'triệu', 'tỷ']

        def number_to_text(num):
            if num == 0:
                return 'không'
            cur_num = str(int(float(num)))
            length = len(cur_num)
            result = []
            
            groups = [cur_num[max(0, length - 3*(i+1)): length - 3*i] for i in range((length // 3) + 1) if cur_num[max(0, length - 3*(i+1)): length - 3*i]]
            groups.reverse()
            
            for idx, group in enumerate(groups):
                n = int(group)
                group_result = []
                
                if n >= 100:
                    group_result.append(units[n // 100] + " trăm")
                    n %= 100
                if n >= 20:
                    group_result.append(tens[n // 10])
                    n %= 10
                elif n >= 10:
                    group_result.append('mười')
                    n %= 10
                if n > 0:
                    group_result.append(units[n])
                
                if group_result:
                    result.append(" ".join(group_result) + " " + thousands[len(groups) - idx - 1])
            
            return " ".join(result).strip()
        
        def decimal_to_text(decimal_part):
            """Đọc 2 chữ số thập phân"""
            if decimal_part == 0:
                return ''
            # Đảm bảo có đúng 2 chữ số
            dec_str = str(int(decimal_part)).zfill(2)
            result = []
            
            # Đọc hàng chục
            if int(dec_str[0]) > 0:
                if int(dec_str[0]) == 1:
                    result.append('mười')
                else:
                    result.append(tens[int(dec_str[0])])
            
            # Đọc hàng đơn vị
            if int(dec_str[1]) > 0:
                if int(dec_str[0]) == 0:
                    # Nếu hàng chục = 0, chỉ đọc đơn vị
                    result.append(units[int(dec_str[1])])
                elif int(dec_str[0]) == 1:
                    # Mười một, mười hai, ...
                    if int(dec_str[1]) == 5:
                        result.append('lăm')
                    elif int(dec_str[1]) == 1:
                        result.append('một')
                    else:
                        result.append(units[int(dec_str[1])])
                else:
                    # Hai mươi một, ba mươi hai, ...
                    if int(dec_str[1]) == 5:
                        result.append('lăm')
                    elif int(dec_str[1]) == 1:
                        result.append('mốt')
                    else:
                        result.append(units[int(dec_str[1])])
            
            return ' '.join(result).strip()
        
        # Kiểm tra currency_id có phải VND không
        is_vnd = False
        if currency_id and currency_id is not True and currency_id is not False:
            try:
                # Nếu là recordset hoặc record
                if hasattr(currency_id, 'name') and not isinstance(currency_id, (bool, int, float, str)):
                    currency_code = currency_id.name
                elif hasattr(currency_id, 'code') and not isinstance(currency_id, (bool, int, float, str)):
                    currency_code = currency_id.code
                elif isinstance(currency_id, (int,)):
                    # Nếu là ID, cần lấy record
                    currency = self.env['res.currency'].browse(currency_id)
                    currency_code = currency.name if currency else ''
                else:
                    currency_code = ''
                is_vnd = currency_code == 'VND'
            except Exception:
                # Nếu không lấy được, mặc định không phải VND
                is_vnd = False
        
        # Xử lý phần nguyên
        integer_part = int(float(amount))
        label = number_to_text(integer_part).strip()
        
        # Xử lý phần thập phân nếu currency != VND
        if not is_vnd:
            # Lấy phần thập phân chính xác 2 chữ số
            amount_str = f"{float(amount):.2f}"
            if '.' in amount_str:
                decimal_str = amount_str.split('.')[1]
                decimal_num = int(decimal_str)
                if decimal_num > 0:
                    decimal_text = decimal_to_text(decimal_num)
                    if decimal_text:
                        label += " phẩy " + decimal_text

        return label[:1].upper() + label[1:].lower()

    @api.model
    def convert_vnd(self, amount):
        return f"{amount:,.0f}"

    @api.model
    def convert_usd(self, amount):
        return f"{amount:,.2f}"

    @api.model
    def convert_date(self, date):
        if date:
            return date.strftime('%d/%m/%Y')
        return ''

    @api.model
    def convert_print(self, date_value):
        if not date_value:
            return ""
        if isinstance(date_value, datetime):
            date_value = date_value.date()
        if isinstance(date_value, fields.Date):
            date_value = datetime.strptime(str(date_value), '%Y-%m-%d').date()
        return date_value.strftime('%d/%m/%Y')

    partner_bank_id = fields.Many2one('res.partner.bank', string="Đơn vị/Cá nhân Thụ Hưởng")
    payment_type = fields.Selection(string="Hình thức thanh toán", selection=[('cash', 'Tiền mặt'), ('bank', 'Chuyển khoản')])

    def _prepare_payment_vals(self):
        res = super(HrExpenseSheet, self)._prepare_payment_vals()
        if self.partner_bank_id:
            res.update({
                'partner_bank_id': self.partner_bank_id.id
            })
        return res

    def _prepare_bill_vals(self):
        res = super(HrExpenseSheet, self)._prepare_bill_vals()
        if self.partner_bank_id:
            res.update({
                'partner_bank_id': self.partner_bank_id.id
            })
        return res

    