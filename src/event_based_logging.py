# Example:  Event based logging for a measurement

from sl3 import *


def prev_logged_value(meas_index):
    """ Searches log for said measurement

    :param meas_index: which measurement to search log for
    :type meas_index: int, e.g. 1 for M1, 12 for M12
    :return: either the reading found in the log, or a reading with bad quality
    :rtype: Reading
    """

    # try to find the log entry
    try:
        l = Log(match=meas_find_label(meas_index), pos=LOG_NEWEST)
        return l.get_newest()
    except LogAccessError:
        return Reading(quality='B')


@MEASUREMENT
def event_based_log_a(value):
    """
    This measurement script is used to decide whether or not to log.
    The goal is to log if there is a significant change between two readings.

    We compare current reading to the previously LOGGED one.
    If the difference is large enough, we log the value, and
    increase the measurement interval.
    If the difference is not significant, we want to log at at much slower rate.
    """

    # significant difference between readings
    threshold = 0.1

    # if the readings are steady, we want to measure slowly
    regular_meas_interval = "00:15:00"

    # if there is a significant difference, we want to measure more frequently
    fast_meas_interval = "00:00:10"

    # how often to log regardless of changes in readings
    minimum_logging_interval_sec = sl3_hms_to_seconds("04:00:00")

    # grab the previously logged value
    prev = prev_logged_value(index())
    if prev.quality == 'G':
        diff = abs(prev.value - value)
        if diff >= threshold:
            # log this value and increase the measurement interval
            meas_log_this()
            setup_write("M{} meas interval".format(index()), fast_meas_interval)
        else:
            # slow down the measurement interval
            setup_write("M{} meas interval".format(index()), regular_meas_interval)

            # if we have not logged in a while. log now
            if (time_scheduled() - prev.time) >= minimum_logging_interval_sec:
                meas_log_this()
            else:
                meas_do_not_log()

    return value
