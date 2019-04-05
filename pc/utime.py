"""
utime.py is a micropython file.
This version lets Satlink code that uses utime run on PC.
"""

# prevent a conflict with the time() function we're going to define
import time as _time

_time_dst = _time.localtime().tm_isdst


def mktime(t):
    """
    This function appends a daylight saving parameter onto mktime tuple to make Python and Micropython compatible.
    Examples::

        >>> import utime
        >>> utime.mktime((2019, 4, 4, 20, 52, 5, 3, 94, 0))
        1554411125.0
        >>> utime.mktime(utime.localtime())
        1554411232.0

    :param: tuple t: tuple time format (year, mon, mday, hour, min, sec, wday, yday)
    :return: time in seconds
    :rtype: float
    """
    return _time.mktime((t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], _time_dst))


def localtime(seconds=None):
    """
    This function appends a daylight saving parameter onto localtime tuple to make Python and Micropython compatible.
    Examples::

        >>> import utime
        >>> utime.localtime(1554411647.48)
        (2019, 4, 4, 21, 0, 47, 3, 94, 0)
        >>> utime.localtime()
        (2019, 4, 4, 21, 2, 12, 3, 94, 0)

    :param: float seconds: Time in seconds. Defaults to current time if no parameter is passed.
    :return: date and time. (year, mon, mday, hour, min, sec, wday, yday, 0)
    :rtype: tuple
    """
    # handle daylight savings time which is relevant on the PC, but not on the Satlink
    if seconds is None:
        t = _time.localtime()
    else:
        t = _time.localtime(seconds)
    return t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], 0


def time():
    return _time.time()


def sleep(seconds):
    _time.sleep(seconds)
