from .time import get_current_datetime


def d(message):
    current_time = get_current_datetime()
    print("{0} [Debug]/{1}".format(current_time, message))


def i(message):
    current_time = get_current_datetime()
    print("{0} [Info]/{1}".format(current_time, message))


def w(message):
    current_time = get_current_datetime()
    print("{0} [Warning]/{1}".format(current_time, message))

