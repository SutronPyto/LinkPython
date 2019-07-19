# Example:  How to prevent Sat/XLink from logging a measurement

from sl3 import *


@MEASUREMENT
def never_log(value):
    """
    Plug this routine into any measurement, and it will never get logged
    no matter what the station settings are
    """

    meas_do_not_log()

    return value
