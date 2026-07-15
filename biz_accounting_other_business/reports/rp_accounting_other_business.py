from odoo import models, api

to_19 = ( u'không', u'một', u'hai', u'ba', u'bốn', u'năm', u'sáu',
          u'bảy', u'tám', u'chín', u'mười', u'mười một', u'mười hai', u'mười ba',
          u'mười bốn', u'mười lăm', u'mười sáu', u'mười bảy', u'mười tám', u'mười chín' )
tens  = ( u'hai mươi', u'ba mươi', u'bốn mươi', u'năm mươi', u'sáu mươi', u'bảy mươi', u'tám mươi', u'chín mươi')
denom = ( '',
          u'nghìn', u'triệu', u'tỷ', u'nghìn tỷ', u'trăm nghìn tỷ')

class rp_accounting_other_business(models.AbstractModel):
    _name = 'report.biz_accounting_other_business.rp_account_other_busi'
    _description = 'rp_accounting_other_business'

    def convert_to_money(self, number):
        str = '{:20,.2f}'.format(number)
        str_list = str.split('.')
        if str_list and int(str_list[1]) == 0:
            str = str_list[0]
        return u'%s'%str.strip()
    
    def _convert_nn(self,val):
        if val>0 and val <= 9:
            return '' + to_19[val]
        if (val > 9 and val < 20) or val==0:
            return  to_19[val]
        for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens)):
            if dval + 10 > val:
                if val % 10:
                    a = u'lăm'
                    if to_19[val % 10] == u'một':
                        a = u'mốt'
                    else:
                        a = to_19[val % 10]
                    return dcap + ' ' + a
                return dcap
    
    def vietnam_number(self,val):
        if val < 100:
            return self._convert_nn(val)
        if val < 1000:
            return self._convert_nnn(val)
        for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
            if dval > val:
                mod = 1000 ** didx
                l = val // mod
                r = val - (l * mod)
                ret = self._convert_nnn(l) + ' ' + denom[didx]
                tmp = u''
                if r > 0:
                    if r < 100:
                        tmp = u'lẻ '
                    ret = ret + ' ' + tmp + self.vietnam_number(r)
                return ret

    def usd_number(self, val):
        """
        Đọc số tiền USD/Euro, xử lý cả phần thập phân (sau dấu phẩy)
        """
        # Nếu là float hoặc có phần thập phân
        try:
            number = float(val)
        except Exception:
            return ''
        int_part = int(number)
        frac_part = round((number - int_part) * 100)

        # Đọc phần nguyên
        if int_part < 100:
            int_text = self._convert_nn(int_part)
        elif int_part < 1000:
            int_text = self._convert_nnn(int_part)
        else:
            for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
                if dval > int_part:
                    mod = 1000 ** didx
                    l = int_part // mod
                    r = int_part - (l * mod)
                    int_text = self._convert_nnn(l) + ' ' + denom[didx]
                    tmp = u''
                    if r > 0:
                        if r < 100:
                            tmp = u'lẻ '
                        int_text = int_text + ' ' + tmp + self.vietnam_number(r)
                    break
            else:
                int_text = self.vietnam_number(int_part)
        # Đọc phần thập phân nếu có
        if frac_part > 0:
            frac_text = self.vietnam_number(frac_part)
            return f"{int_text} phẩy {frac_text}"
        else:
            return int_text
    
    def _convert_nnn(self,val):
        word = ''
        tmp = ''
        (mod, rem) = (val % 100, val // 100)
        if rem > 0:
            word = to_19[rem] + u' trăm'
            if mod > 0:
                word = word + ' '
            if mod < 10:
                tmp = u'lẻ '
        if mod > 0:
            word = word + tmp + self._convert_nn(mod)
        return word
    
    def amount_to_text(self,number, currency_id):
        if currency_id.name == 'VND':
            number = abs(number)
            number = '%.2f' % number
            list = str(number).split('.')
            start_word = self.vietnam_number(int(list[0]))
            currency_label = currency_id.currency_unit_label or currency_id.full_name
            final_result = ' '.join([start_word[0].upper()+ start_word[1:], (currency_label.lower() if currency_label else "")])
            return final_result
        else:
            # Xử lý các loại tiền khác (USD, EUR, ...)
            number = abs(number)
            
            # Xử lý riêng cho USD với cents sử dụng currency labels
            currency_name = currency_id.name
            try:
                number = float(number)
            except Exception:
                return ''
            int_part = int(number)
            frac_part = round((number - int_part) * 100)
            
            # Đọc phần chính (đô la, euro, etc.)
            main_text = self.vietnam_number(int_part)
            
            # Đọc phần phụ (cents, cents euro, etc.)
            subunit_text = ''
            if frac_part > 0:
                subunit_text = self.vietnam_number(frac_part)
            
            # Sử dụng currency labels từ Odoo
            unit_label = currency_id.currency_unit_label or currency_name
            unit_label = unit_label.lower() if unit_label else ""
            subunit_label = currency_id.currency_subunit_label or 'cents'
            subunit_label = subunit_label.lower() if subunit_label else ""
            
            # Ghép kết quả
            if frac_part > 0:
                if int_part > 0:
                    text_result = f"{main_text} {unit_label} và {subunit_text} {subunit_label}"
                else:
                    text_result = f"{subunit_text} {subunit_label}"
            else:
                text_result = f"{main_text} {unit_label}"
            
            # Viết hoa chữ cái đầu
            if text_result:
                final_result = text_result[0].upper() + text_result[1:]
            else:
                final_result = text_result
            return final_result

    def format_float_number(self, num):
        if not num:
            return 0

        number = float(num)
        if number % 1 == 0:
            return "{:,.0f}".format(number).replace(',','.')
        else:
            number_format = "{:,.2f}".format(number).rstrip('0')
            numbers = number_format.split('.')
            return numbers[0].replace(',','.') + ',' + numbers[1]

    def get_lines(self, move):
        lines = []
        debit_lines = move.line_ids.filtered(lambda x: x.debit > 0)
        credit_lines = move.line_ids.filtered(lambda x: x.credit > 0)

        if len(debit_lines) >= len(credit_lines):
            move_lines = debit_lines
        else:   
            move_lines = credit_lines

        for line in move_lines:
            account = line.account_id.code
            ctp_account = line.ctp_account_ids and ', '.join(line.ctp_account_ids.mapped('code')) or ''
            print("~~ctp_account",ctp_account)
            lines.append({
                'name': line.name,
                'debit': line.debit > 0 and account or ctp_account,
                'credit': line.credit > 0 and account or ctp_account,
                'amount': abs(line.balance) if move.currency_id == move.company_id.currency_id else abs(line.amount_currency)
            })
        return lines

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env['account.move']
        docs = model.browse(docids)
        return {
            'doc_model': model,
            'docs': docs,
            'amount_to_text': self.amount_to_text,
            'format_float_number': self.format_float_number,
            'get_lines': self.get_lines
        }
