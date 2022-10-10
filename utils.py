from math import sin, cos, sqrt, atan2, radians
from datetime import datetime, timedelta

def time_delta(int_time:int,delta:int) -> int:

    '''Only accepts date in format 20211201 as a integer. positive delta indicates
    that is a sum, negative delta indicates that is a subtraction'''

    int_time = datetime.strptime(str(int_time), '%Y%m%d')

    int_time = int_time + timedelta(days = int(delta))

    return int_time.year*10000 + int_time.month*100 + int_time.day*1

def distance_latLong(lat1,lon1,lat2,lon2):

    # approximate radius of earth in km
    R = 6373.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    if R * c == 0:
        distance = 1.0
    else:
        distance = R * c

    return distance