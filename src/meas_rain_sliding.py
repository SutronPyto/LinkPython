# Example:  Computes rainfall during the last 60 and last 90 minutes

"""
Computes rainfall during the last 60 minutes and 90 minutes.
These rainfall measurements are made every five minutes.

For example, at 08:45, this module will report 60 min rainfall since 07:45.
It will also report 90 min rainfall since 07:15.

At 08:50, this module will report 60 min rainfall since 07:50,
and 90 min rainfall since 07:20.

A precip accumulation measurement named "RAIN ACCU" must be present in the system.

The 60 and 90 minute measurements compute rainfall by comparing the current rain
accumulation reading to the reading logged 60 and 90 minutes ago.
For that reason, "RAIN ACCU" must be logged.

Additionally, "RAIN ACCU" measurement must be scheduled at least as frequently as
the 60 and 90 minute rainfall measurements.

A Sat/XLink setup is associated with this module:
`meas_rain_sliding_setup.txt <meas_rain_sliding_setup.txt>`_

This module is a variation of:
`meas_daily_roc.py <meas_daily_roc.html>`_
"""

from sl3 import *


def differential_reading(meas_label, period_sec, allow_negative):
    """
    Computes the difference between the most recent reading of the specified measurement,
    and an older reading of the same measurement.
    Routine reads the log looking for the older reading.

    :param meas_label: the label of the measurement in question
    :type meas_label: str
    :param period_sec: how long ago the old reading was made in seconds
    :type period_sec: int
    :param allow_negative: should a negative difference be allowed?  set to False for rain accumulation
    :type allow_negative: bool
    :return: the difference between the two readings
    :rtype: float
    """

    # current reading
    current = measure(meas_as_index(meas_label))

    # compute previous time based on current reading and period_sec
    time_old = current.time - period_sec

    # Read the log, looking for the measurement starting with the newest
    # and going backwards until we find the oldest reading within the time bounds.
    oldest_reading = Reading(value=0.0)
    try:
        logthing = Log(oldest=time_old,
                       newest=current.time,
                       match=meas_label,
                       pos=LOG_NEWEST)

        for itero in logthing:
            oldest_reading = itero

    except LogAccessError:
        print('No logged readings found.  Normal until recording starts.')
        return 0.0

    # if both readings are valid, compute the difference
    if (current.quality == 'G') and (oldest_reading.quality == 'G'):
        result = current.value - oldest_reading.value

        if (result < 0.0) and (not allow_negative):
            # If the difference is negative, the measurement has been reset.
            print('Negative change not allowed')
            return current.value
        else:
            print('Change computed successfully')
            return result

    else:
        print('Readings were not valid')
        return 0.0


@MEASUREMENT
def rain_60_min(inval):
    """
    Computes the rainfall during the last 60 minutes.
        Another measurement labeled RAIN ACCU must be recording precip accumulation.
    """
    return differential_reading("RAIN ACCU", 3600, False)  # 3600 sec = 1 hour.  False means no negative readings.


@MEASUREMENT
def rain_90_min(meas_index_or_label):
    """
    Computes the rainfall during the last 90 minutes.
        Another measurement labeled RAIN ACCU must be recording precip accumulation.
    """
    return differential_reading("RAIN ACCU", 5400, False)  # 5400 sec = 1.5 hour.  False means no negative readings.
