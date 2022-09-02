import datetime
import time


def convert_ms_to_time(millis: int) -> str:
    seconds = int(millis / 1000)
    minutes = int(seconds / 60)
    seconds = int(seconds % 60)
    hours = int(minutes / 60)
    minutes = int(minutes % 60)

    return "{0}h {1}m {2}s".format(hours, minutes, seconds)


def convert_discord_time_to_ms(time_count: int, time_unit: str) -> int:
    if time_unit == "s":
        return time_count * 1000
    elif time_unit == "m":
        return time_count * 60 * 1000
    elif time_unit == "h":
        return time_count * 60 * 60 * 1000
    else:
        return -1


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


def get_current_time_as_ms() -> int:
    return int(round(time.time() * 1000))
