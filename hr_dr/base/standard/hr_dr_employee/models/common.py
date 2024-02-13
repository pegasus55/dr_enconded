import pytz

def convert_utc_time_to_tz(utc_dt, tz_name):
    """
    Method to convert UTC time to local time
    :param utc_dt: datetime in UTC
    :param tz_name: the name of the timezone to convert. In case of no tz_name passed, this method will try to find the timezone in context or the login user record

    :return: datetime object presents local time
    """
    tz = pytz.timezone(tz_name)
    return pytz.utc.localize(utc_dt, is_dst=None).astimezone(tz)

def convert_time_to_utc(self, dt, tz_name):
    """
    @param dt: datetime obj to convert to UTC
    @param tz_name: the name of the timezone to convert. In case of no tz_name passed, this method will try to find the timezone in context or the login user record

    @return: an instance of datetime object
    """
    local = pytz.timezone(tz_name)
    local_dt = local.localize(dt, is_dst=None)
    return local_dt.astimezone(pytz.utc)

def days2ymd(days):
    avgyear = 365.2425
    avgmonth = 365.2425 / 12.0

    years, remainder = divmod(days, avgyear)
    years = int(years)
    months, remainder = divmod(remainder, avgmonth)
    months = int(months)
    days = int(remainder)

    return {'y': years, 'm': months, 'd': days}

def seconds2hms(seconds):
    avghour = 3600.0
    avgminute = 60.0

    negative = True
    if seconds >= 0:
        negative = False
    seconds = abs(seconds)

    hours, remainder = divmod(seconds, avghour)
    hours = int(hours)

    minutes, remainder = divmod(remainder, avgminute)
    minutes = int(minutes)

    seconds = int(remainder)

    cadena = ""
    if negative:
        cadena = "- {}:{}:{}".format("0{}".format(hours) if hours <= 9 else hours,
                                     "0{}".format(minutes) if minutes <= 9 else minutes,
                                     "0{}".format(seconds) if seconds <= 9 else seconds)
    else:
        cadena = "{}:{}:{}".format("0{}".format(hours) if hours <= 9 else hours,
                                   "0{}".format(minutes) if minutes <= 9 else minutes,
                                   "0{}".format(seconds) if seconds <= 9 else seconds)

    return {'h': hours, 'm': minutes, 's': seconds, 'c': cadena}