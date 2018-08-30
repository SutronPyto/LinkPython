"""
utime.py is a micropython file.
This version lets Satlink code that uses utime run on PC.
"""

# prevent a conflict with the time() function we're going to define
import time as _time

_time_dst = _time.localtime().tm_isdst


def mktime(t):
    # handle daylight savings time which is relevant on the PC, but not on the Satlink
    return _time.mktime((t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], _time_dst))


def localtime(seconds=None):
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
