from .time import get_current_datetime


def d(tag: str, message):
    current_time = get_current_datetime()
    print("{0} [Debug]/{1}: {2}".format(current_time, tag, message))


def i(tag: str, message):
    current_time = get_current_datetime()
    print("{0} [Info]/{1}: {2}".format(current_time, tag, message))


def w(tag: str, message):
    current_time = get_current_datetime()
    print("{0} [Warning]/{1}: {2}".format(current_time, tag, message))


def e(tag: str, message):
    current_time = get_current_datetime()
    print("{0} [Error]/{1}: {2}".format(current_time, tag, message))
