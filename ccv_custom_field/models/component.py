to_19 = ( u'không', u'một', u'hai', u'ba', u'bốn', u'năm', u'sáu',
          u'bảy', u'tám', u'chín', u'mười', u'mười một', u'mười hai', u'mười ba',
          u'mười bốn', u'mười lăm', u'mười sáu', u'mười bảy', u'mười tám', u'mười chín' )
tens  = ( u'hai mươi', u'ba mươi', u'bốn mươi', u'năm mươi', u'sáu mươi', u'bảy mươi', u'tám mươi', u'chín mươi')
denom = ( '', u'nghìn', u'triệu', u'tỷ', u'nghìn tỷ', u'trăm nghìn tỷ')


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

def format_float_number_weight(num):
    if not num:
        return "0,00"

    number = float(num)
    number_format = "{:,.3f}".format(number)
    parts = number_format.split('.')
    return parts[0].replace(',', '.') + ',' + parts[1]

def vietnam_number_upper(number):
    from num2words import num2words
    try:
        text = num2words(number, lang='vi')
        return text.capitalize() + " đồng"
    except:
        return ""

def split_string_to_lines(s, sep_char, count):
    result = []
    counter = 0
    start = 0
    for i, c in enumerate(s):
        if c == sep_char:
            counter += 1
            if counter % count == 0:
                result.append(s[start:i+1])
                start = i+1
    if start < len(s):
        result.append(s[start:])
    return '\n'.join(result)
