to_19 = ( u'không', u'một', u'hai', u'ba', u'bốn', u'năm', u'sáu',
          u'bảy', u'tám', u'chín', u'mười', u'mười một', u'mười hai', u'mười ba',
          u'mười bốn', u'mười lăm', u'mười sáu', u'mười bảy', u'mười tám', u'mười chín' )
tens  = ( u'hai mươi', u'ba mươi', u'bốn mươi', u'năm mươi', u'sáu mươi', u'bảy mươi', u'tám mươi', u'chín mươi')
denom = ( '', u'nghìn', u'triệu', u'tỷ', u'nghìn tỷ', u'trăm nghìn tỷ')

def format_date(date):
    return date.strftime('%d/%m/%Y')

def format_date_vi(date):
    return date.strftime('Ngày %d tháng %m năm %Y')

def _convert_nn(val):
    # Convert float to int to avoid TypeError with tuple indices
    val = int(val)
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
    return ''  # Return empty string if no match found


def vietnam_number(val):
    # Convert float to int to avoid TypeError with tuple indices
    val = int(val)
    # Kiểm tra nếu 3 số cuối là 000 thì đọc là "đồng chẵn"
    if val % 1000 == 0 and val >= 1000:
        result = _vietnam_number_without_dong(val)
        return result + ' đồng chẵn'
    
    if val < 100:
        return _convert_nn(val) + ' đồng'
    if val < 1000:
        return _convert_nnn(val, add_dong=True)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            left_part = val // mod
            r = val - (left_part * mod)
            # Nếu left_part < 100 và đây là phần nghìn (didx=1), cần thêm "không trăm"
            if left_part < 100 and didx == 1:
                ret = _convert_nnn(left_part, add_dong=False, force_hundred=True) + ' ' + denom[didx]
            else:
                ret = _convert_nnn(left_part, add_dong=False) + ' ' + denom[didx]
            tmp = u''
            if r > 0:
                if r < 100:
                    # Nếu r < 100 và đây là phần đơn vị (sau phần nghìn trở lên), đọc "không trăm" thay vì "lẻ"
                    if didx >= 1:
                        if r < 10:
                            # Trường hợp 001 -> không trăm lẻ một
                            tmp = u'không trăm lẻ '
                        else:
                            tmp = u'không trăm '
                    else:
                        tmp = u'lẻ '
                elif r < 1000 and r // 100 == 0:
                    # Trường hợp r có 3 chữ số nhưng hàng trăm = 0 (ví dụ: 099, 001)
                    if r % 100 < 10 and r % 100 > 0:
                        # Trường hợp 001 -> không trăm lẻ một
                        tmp = u'không trăm lẻ '
                    else:
                        tmp = u'không trăm '
                ret = ret + ' ' + tmp + _vietnam_number_without_dong(r)
            return ret + ' đồng'


def _vietnam_number_without_dong(val, need_hundred=False):
    # Convert float to int to avoid TypeError with tuple indices
    val = int(val)
    if val < 100:
        if need_hundred and val > 0:
            return u'không trăm ' + _convert_nn(val)
        return _convert_nn(val)
    if val < 1000:
        return _convert_nnn(val, add_dong=False)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            left_part = val // mod
            r = val - (left_part * mod)
            # Nếu left_part < 100 và đây là phần nghìn (didx=1), cần thêm "không trăm"
            if left_part < 100 and didx == 1:
                ret = _convert_nnn(left_part, add_dong=False, force_hundred=True) + ' ' + denom[didx]
            else:
                ret = _convert_nnn(left_part, add_dong=False) + ' ' + denom[didx]
            tmp = u''
            if r > 0:
                if r < 100:
                    # Nếu r < 100 và đây là phần đơn vị (sau phần nghìn trở lên), đọc "không trăm" thay vì "lẻ"
                    if didx >= 1:
                        if r < 10:
                            # Trường hợp 001 -> không trăm lẻ một
                            tmp = u'không trăm lẻ '
                        else:
                            tmp = u'không trăm '
                    else:
                        tmp = u'lẻ '
                elif r < 1000 and r // 100 == 0:
                    # Trường hợp r có 3 chữ số nhưng hàng trăm = 0 (ví dụ: 099, 001)
                    if r % 100 < 10 and r % 100 > 0:
                        # Trường hợp 001 -> không trăm lẻ một
                        tmp = u'không trăm lẻ '
                    else:
                        tmp = u'không trăm '
                ret = ret + ' ' + tmp + _vietnam_number_without_dong(r)
            return ret
    return ''

def _convert_nnn(val, add_dong=False, force_hundred=False):
    # Convert float to int to avoid TypeError with tuple indices
    val = int(val)
    word = ''
    tmp = ''
    (mod, rem) = (val % 100, val // 100)
    
    # Xử lý trường hợp có hàng trăm
    if val >= 100:
        if rem > 0:
            word = to_19[rem] + u' trăm'
        else:
            # Trường hợp không trăm (ví dụ: 014, 099)
            word = u'không trăm'
        if mod > 0:
            word = word + ' '
        if mod < 10 and mod > 0:
            tmp = u'lẻ '
    elif force_hundred and val > 0:
        # Trường hợp cần thêm "không trăm" cho số < 100 (ví dụ: 14 -> không trăm mười bốn)
        word = u'không trăm '
        if mod < 10 and mod > 0:
            tmp = u'lẻ '
    
    if mod > 0:
        word = word + tmp + _convert_nn(mod)
    
    if add_dong:
        return word + ' đồng'
    return word

def format_float_number(number):
    if number >= 0:
        if number % 1 == 0:
            number_format = "{:,.0f}".format(number)
        else:
            number_format = "{:,.2f}".format(number)
    else:
        number = abs(number)
        if number % 1 == 0:
            number_format = "(" + "{:,.0f}".format(number) + ")"
        else:
            number_format = "(" + "{:,.2f}".format(number) + ")"
    return number_format
