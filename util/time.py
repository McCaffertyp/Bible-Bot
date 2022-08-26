import datetime


def get_current_datetime() -> str:
    time_now = datetime.datetime.now()
    year = time_now.year
    month = time_now.month
    day = time_now.day
    hour = time_now.hour
    minute = time_now.minute
    second = time_now.second

    return "{0}-{1}-{2} {3}:{4}:{5}".format(year, month, day, hour, minute, second)
