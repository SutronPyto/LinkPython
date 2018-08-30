# Example:  demonstrates custom tx formatting from the log

from sl3 import *
import utime


# this variable is used to task_meas_a1
vc = 0.0


@TASK
def task_meas_a1():
    """
    This task logs a value.
    It is expected to run periodically.

    :return: None
    """
    global vc
    vc += 0.1
    r = Reading(time=time_scheduled(), label="MT1", value=vc, right_digits=2)
    r.write_log()


@TXFORMAT
def format_a1(standard):
    """
    Prepares data for a transmission.
        * Reads the log looking for specific log entries.
        * Once found, the data is formatted into a CSV style format.

    :param standard: standard input string which is ignored
    :return: formatted tx data
    :rtype: string
    """

    """ figure out he timestamps of the data we want to tx
    time_scheduled gives us the time of this tx
    however, Satlink formats up transmission data a little while before tx time
    the window we want the data form is the same as the tx interval
    if tx interval were 15 min, and it were 12:00:00, we would want data from
    11:44:01 to 11:59:00
    """
    time_recent = time_scheduled() - 60
    interval_in_sec = sl3_hms_to_seconds(setup_read("TX3 Scheduled Interval"))
    time_oldest = time_recent - interval_in_sec + 1  # +1 to avoid redundant data

    # our result goes into this string
    formatted = ""

    # did we find any data to format?
    found_data = False

    # diagnostics:
    formatted += "actualtime " + ascii_time(utime.time()) + '\r\n'
    formatted += "tx    time " + ascii_time(time_scheduled()) + '\r\n'
    formatted += "stop  time " + ascii_time(time_recent) + '\r\n'
    formatted += "start time " + ascii_time(time_oldest) + '\r\n'
    formatted += "and now the data:\r\n"

    try:
        # setup the log bound by label and time
        l = Log(match="MT1", oldest=time_oldest, newest=time_recent)

        # get the first reading and add it to the format string
        formatted += str(l.get_newest())
        formatted += '\r\n'
        found_data = True  # otherwise we would go to exception

        # format up every log entry we find
        for r in l:
            formatted += str(r)
            formatted += '\r\n'

    except LogAccessError:
        # we did not find all the entries we expected
        formatted += standard

    # if we found no data, transmit data buffer empty
    if not found_data:
        formatted += "Data Buffer Empty"

    return formatted
