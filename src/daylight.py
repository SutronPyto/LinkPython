# Example:  demonstrates accumulating minutes of daylight

from sl3 import *

"""this variable counts the minutes of daylight"""
m_daylight = 0.0


@MEASUREMENT
def minutes_of_daylight(pv):
    """
    This program counts minutes of daylight in a 24 hour period.
    The following measurement setup configuration is assumed:
    Analog type for PV reading, measurement interval is one minute

    :param pv: analog reading form PV sensor
    :return: number of daylight minutes so far
    """
    global m_daylight

    if pv > 0.8:
        """ a reading greater than this value indicates daylight """
        m_daylight += 1.0

    if ascii_time_hms(time_scheduled()) == "00:00:00":
        """ at midnight, reset the counter"""
        m_daylight = 0.0

    return m_daylight
