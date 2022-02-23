"""
Tx format script adds a time and special character before each line of ASCII column format
changes spaces between measurements to commas
also arranges lines of data from newest first to oldest first
Please note that the time stamp is computed based on transmission time and the 10 min measurement interval, so if the tx happens between 19:20:00 and 19:29:59, the newest timestamp is set to 19:20:20.  Note that there are some cases in which this may not be correct (right near the top of the 10 minute mark).
The script is built for 10 minute data.

E.g. input
6 6 85.2 85.2 22.5 45 850.4 0.00 -51
6 6 85.2 85.2 22.5 45 850.4 0.00 -69
6 6 85.2 85.2 22.5 45 850.4 0.00 -58
6 6 85.2 85.2 22.5 45 850.4 0.00 -40

e.g. output
2 10:40:00 6,6,85.2,85.2,22.5,45,850.4,0.00,-40
2 10:50:00 6,6,85.2,85.2,22.5,45,850.4,0.00,-58
2 11:00:00 6,6,85.2,85.2,22.5,45,850.4,0.00,-69
2 11:10:00 6,6,85.2,85.2,22.5,45,850.4,0.00,-51

"""

from sl3 import *


def format_mod_column_time(column_format, time_tx, meas_interval):
    """
    modifies ASCII column format as noted above

    :param column_format: ASCII column formatted data
    :type column_format: str
    :param time_tx: transmission time in seconds in day
    :type time_tx: int
    :param meas_interval: measurement interval in seconds
    :type meas_interval: int
    :return: modified format
    :rtype: str
    """

    # compute meas time based on transmission time and meas  interval
    time_newest = (time_tx // meas_interval) * meas_interval

    lines = column_format.strip().split("\r\n")
    new_format = ""

    # arrange lines of data from oldest first to newest first
    for i in range(len(lines)-1, -1, -1):
        # compute time of this
        time_this = time_newest - (i * meas_interval)
        line_space_to_comma = lines[i].replace(" ", ",")

        convert_one = "2 {} {}\r\n".format(ascii_time_hms(time_this), line_space_to_comma)
        new_format += convert_one
    return new_format


@TXFORMAT
def format_mod_column(column_format):
    """see format_mod_column_time"""

    # the measurement interval is fixed
    meas_interval_sec = 10*60  # 10 min in seconds

    return format_mod_column_time(column_format, time_scheduled(), meas_interval_sec)


""" for testing on PC"""
if not sutron_link:
    time_tx = sl3_time_to_seconds("2022/02/22 11:12:32")
    column_format = "6 6 85.2 85.2 22.5 45 850.4 0.00 -51\r\n6 6 85.2 85.2 22.5 45 850.4 0.00 -69\r\n6 6 85.2 85.2 22.5 45 850.4 0.00 -58\r\n6 6 85.2 85.2 22.5 45 850.4 0.00 -40\r\n"
    reformatted = format_mod_column_time(column_format, time_tx, 600)
    print(reformatted)
    expected = "2 10:40:00 6,6,85.2,85.2,22.5,45,850.4,0.00,-40\r\n2 10:50:00 6,6,85.2,85.2,22.5,45,850.4,0.00,-58\r\n2 11:00:00 6,6,85.2,85.2,22.5,45,850.4,0.00,-69\r\n2 11:10:00 6,6,85.2,85.2,22.5,45,850.4,0.00,-51\r\n"
    assert(reformatted == expected)
