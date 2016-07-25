import datetime

def sec_to_timedelta_str(seconds):
    timedelta_str = []
    for sec in seconds:
       timedelta_str.append(str(datetime.timedelta(seconds=float(sec)))) 
    return timedelta_str
