# Example:  Change a setup field based upon the date
from sl3 import *


def get_value_for_date(month, day):
    """
    returns the value associated with the provided date
    values are stored in the table below and are associated with
        a start and an end date
    put the range of dates and associated values in the table below
    in the format month, day
    e.g. {'start': (2, 5), 'end': (6, 1),   'value': 2},
        means that from Feb 5th to Jun 1st, the value is 2
    """
    # YOU MUST HAVE THE FIRST OF THE YEAR AS A DATE IN THE TABLE
    # The entire year should be handled by the table
    # if not, default_value is used (see below)
    ranges = [
        {'start': (1, 1), 'end': (2, 1),   'value': 1}, # MUST DEFINE FIRST OF YEAR!
        {'start': (2, 2), 'end': (5, 7),   'value': 2.9218},
        {'start': (5, 8), 'end': (6, 1),   'value': 4},
        {'start': (6, 2), 'end': (9, 1),   'value': 5},
        {'start': (9, 2), 'end': (12, 31), 'value': 33},
    ]

    # if a date is not in the table, this value is returned
    default_value = 0

    def is_in_range(m, d, start, end):
        start_m, start_d = start
        end_m, end_d = end
        if (start_m < end_m) or (start_m == end_m and start_d <= end_d):
            return ((m > start_m) or (m == start_m and d >= start_d)) and \
                   ((m < end_m) or (m == end_m and d <= end_d))
        else:
            return ((m > start_m) or (m == start_m and d >= start_d)) or \
                   ((m < end_m) or (m == end_m and d <= end_d))

    for entry in ranges:
        if is_in_range(month, day, entry['start'], entry['end']):
            return entry['value']

    return default_value


def test_get_value_for_date():
    """ test routine for get_value_for_date """
    # Days in each month for a non-leap year
    month_lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    prev_value = None
    for month in range(1, 13):
        for day in range(1, month_lengths[month - 1] + 1):
            current_value = get_value_for_date(month, day)
            if prev_value is not None and current_value != prev_value:
                print("Change on {}-{}: {} -> {}".format(month, day, prev_value, current_value))
            prev_value = current_value


def month_day(time_t):
    """
    returns the month, day of the provided timestamp
    :param time_t: two options:
        time as a float number of seconds since 1970, just like utime.time()
        time as a tuple, as per utime.localtime()
    :return: month, day
    :rtype: int
    """
    # if it is not already, convert time to a tuple as per localtime()
    if type(time_t) is float:
        time_t = utime.localtime(time_t)

    return time_t[1], time_t[2]


@TASK
def change_setup_field():
    """
    changes setup field based upon the day of the year
    recommend the task be run once every day at midnight
    """
    current_time = utime.localtime()
    month, day = month_day(current_time)
    value = get_value_for_date(month, day)

    # change a setup field with the value
    setup_write("GP1 Value", value)
    #setup_write("M1 Alarm Threshold", value)
