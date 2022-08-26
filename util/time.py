import datetime


def get_current_datetime() -> str:
    time_now = datetime.datetime.now()
    year = time_now.year
    month = time_now.month
    day = time_now.day
    hour = time_now.hour
    if int(hour) < 10:
        hour = "0{0}".format(hour)
    minute = time_now.minute
    if int(minute) < 10:
        minute = "0{0}".format(minute)
    second = time_now.second
    if int(second) < 10:
        second = "0{0}".format(second)

    return "{0}-{1}-{2} {3}:{4}:{5}".format(year, month, day, hour, minute, second)
