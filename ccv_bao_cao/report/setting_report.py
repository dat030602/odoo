from odoo import fields, models, api

to_19 = ( u'không', u'một', u'hai', u'ba', u'bốn', u'năm', u'sáu',
          u'bảy', u'tám', u'chín', u'mười', u'mười một', u'mười hai', u'mười ba',
          u'mười bốn', u'mười lăm', u'mười sáu', u'mười bảy', u'mười tám', u'mười chín' )
tens  = ( u'hai mươi', u'ba mươi', u'bốn mươi', u'năm mươi', u'sáu mươi', u'bảy mươi', u'tám mươi', u'chín mươi')
denom = ( '',
          u'nghìn', u'triệu', u'tỷ', u'nghìn tỷ', u'trăm nghìn tỷ')

def _convert_nn(val):
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

def vietnam_number(val):
    if val < 100:
        return _convert_nn(val)
    if val < 1000:
        return _convert_nnn(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            ret = _convert_nnn(l) + ' ' + denom[didx]
            tmp = u''
            if r > 0:
                if r < 100:
                    tmp = u'lẻ '
                ret = ret + ' ' + tmp + vietnam_number(r)
            return ret

def _convert_nnn(val):
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
        word = word + tmp + _convert_nn(mod)
    return word

def amount_to_text(number):
    am = False
    if number < 0:
        am = True

    number = abs(number)
    number = '%.2f' % number
    list = str(number).split('.')
    start_word = vietnam_number(int(list[0]))
    final_result = start_word[0].upper()+ start_word[1:]
    if am:
        final_result = "Âm %s" % final_result.lower()

    return final_result

def format_date_vn(date, start=False):
    if not date:
        date_string = 'Ngày........tháng........năm........'
    else:
        date_string = date.strftime('Ngày %d tháng %d năm %Y')

    if not start:
        date_string = date_string.lower()

    return date_string

def format_float_number(num):
    if not num:
        return 0

    number = float(num)
    if number % 1 == 0:
        return "{:,.0f}".format(number).replace(',','.')
    else:
        number_format = "{:,.2f}".format(number).rstrip('0')
        numbers = number_format.split('.')
        return numbers[0].replace(',','.') + ',' + numbers[1]

def get_address(partner_id):
    if not partner_id:
        return ''
    address_parts = []
    
    if partner_id.street:
        address_parts.append(partner_id.street)
    
    if partner_id.wards_id:
        address_parts.append(partner_id.wards_id.name) 
    
    if partner_id.district_id:
        address_parts.append(partner_id.district_id.name)
    
    if partner_id.state_id:
        address_parts.append(partner_id.state_id.name)
    
    if partner_id.country_id:
        address_parts.append(partner_id.country_id.name)

    full_address = ', '.join(address_parts)
    return full_address

class de_xuat_thue_xe(models.AbstractModel):
    _name = 'report.ccv_bao_cao.de_xuat_thue_xe'
    _description = 'de_xuat_thue_xe'

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env['account.move']
        docs = model.browse(docids)
        return {
            'doc_model': model,
            'docs': docs,
            'amount_to_text': amount_to_text,
            'format_float_number': format_float_number,
            'format_date_vn': format_date_vn,
            'get_address': get_address,
            'vietnam_number': vietnam_number,
        }
