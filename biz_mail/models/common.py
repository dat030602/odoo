

from datetime import datetime, timedelta

def convert_datetime(imput_date):
    nweek = datetime.strptime(str(imput_date), '%Y-%m-%d %H:%M:%S')
    new_hour, ampm = hour24_to_ampm(nweek.hour)
    str_format = '%H:%M %p' if imput_date.strftime('%Y-%m-%d')==datetime.now().strftime('%Y-%m-%d') else '%H:%M %p %a'
    return nweek.strftime(str_format)

def hour24_to_ampm(hour):
    ampm = "AM" if hour < 12 else "PM"
    new_hour = (hour - 1) % 12 + 1
    return new_hour, ampm
